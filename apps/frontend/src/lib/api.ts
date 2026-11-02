/** Cliente HTTP para la API de Luma Bank. */
import { clearSession, getAccessToken, getRefreshToken, updateTokens } from "./auth";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  payload: unknown;
  code: string;
  constructor(status: number, payload: unknown) {
    super(extractMessage(payload, status));
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
    const code = (payload as { code?: unknown } | null)?.code;
    this.code = typeof code === "string" ? code : "";
  }
}

function extractMessage(payload: unknown, status: number): string {
  if (payload && typeof payload === "object") {
    const p = payload as Record<string, unknown>;
    if (typeof p.detail === "string") return p.detail;
    // errores de validación de DRF: { campo: ["msg", ...] } o { non_field_errors: [...] }
    for (const value of Object.values(p)) {
      if (Array.isArray(value) && typeof value[0] === "string") return value[0];
      if (typeof value === "string") return value;
    }
  }
  return `Error ${status}`;
}

let refreshing: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  const res = await fetch(`${API_URL}/api/v1/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "omit",
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) {
    // Token vencido o inválido: la sesión terminó (el layout privado redirige al login).
    if (res.status === 401) clearSession();
    return false;
  }
  const data = (await res.json()) as { access: string; refresh?: string };
  updateTokens(data.access, data.refresh ?? refresh);
  return true;
}

/** Renueva el JWT. Las llamadas simultáneas comparten una sola renovación. */
export function refreshSession(): Promise<boolean> {
  refreshing ??= doRefresh().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

async function send(method: string, path: string, body: unknown, auth: boolean): Promise<Response> {
  const attempt = () => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (auth) {
      const token = getAccessToken();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    return fetch(`${API_URL}${path}`, {
      method,
      headers,
      // El SPA se autentica con JWT en el header Authorization, nunca con cookies.
      // Así una sesión del admin de Django abierta en el mismo navegador no
      // "contamina" las peticiones de la API (evita fallos de CSRF).
      credentials: "omit",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  };
  const res = await attempt();
  // Un 401 con el token vencido no llegó a ejecutar nada: es seguro reintentar.
  if (auth && res.status === 401 && (await refreshSession())) return attempt();
  return res;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = false,
): Promise<T> {
  const res = await send(method, path, body, auth);
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // respuesta no-JSON (p. ej. traceback HTML de un 500)
    if (!res.ok) {
      throw new ApiError(res.status, {
        detail:
          res.status >= 500
            ? "El servidor tuvo un error. Revisa los logs del backend."
            : `Error ${res.status}`,
      });
    }
  }
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export const apiGet = <T>(path: string, auth = false) => request<T>("GET", path, undefined, auth);
export const apiPost = <T>(path: string, body?: unknown, auth = false) =>
  request<T>("POST", path, body, auth);

// --- Endpoints ---------------------------------------------------------

export interface HealthResponse {
  status: string;
  service: string;
  dni_validation_mode: string;
  debug: boolean;
  checks: Record<string, string>;
}
export const getHealth = () => apiGet<HealthResponse>("/api/health/");

export interface DniValidation {
  dni: string;
  nombres: string;
  apellidos: string;
  nombre_completo: string;
}
export const validarDni = (dni: string) =>
  apiPost<DniValidation>("/api/v1/accounts/registro/validar-dni/", { dni });

export interface RegistroPayload {
  dni: string;
  identity_confirmed: boolean;
  birth_date: string; // YYYY-MM-DD
  email: string;
  password: string;
  liveness: { passed: boolean; checks: string[] };
  face_descriptor: number[];
  descriptor_algorithm: string;
}
export interface RegistroResponse {
  account_number: string;
  email: string;
  full_name: string;
  totp: { secret: string; otpauth_uri: string; issuer: string };
  message: string;
}
export const registrar = (payload: RegistroPayload) =>
  apiPost<RegistroResponse>("/api/v1/accounts/registro/", payload);

// --- HU03: login -----------------------------------------------------

export interface LoginSuccess {
  access: string;
  refresh: string;
  user: { email: string; full_name: string; dni: string | null };
}
export interface LoginChallenge {
  detail: string;
  fallback?: "password_totp";
  locked_until?: string;
}

export const loginFacial = (
  identifier: string,
  face_descriptor: number[],
  liveness: { passed: boolean; checks: string[] },
) =>
  apiPost<LoginSuccess>("/api/v1/accounts/login/facial/", {
    identifier,
    face_descriptor,
    liveness,
  });

export const loginPassword = (identifier: string, password: string, totp: string) =>
  apiPost<LoginSuccess>("/api/v1/accounts/login/password/", { identifier, password, totp });

export interface Me {
  email: string;
  full_name: string;
  dni: string | null;
  accounts: {
    number: string;
    currency: string;
    status: string;
    balance: string;
    opened_at: string;
  }[];
}
export const getMe = () => apiGet<Me>("/api/v1/accounts/me/", true);

// --- Banca: cuentas, saldo y TREA ------------------------------------

export interface SavingsRate {
  currency: string;
  trea: string;
  valid_from: string;
}
export interface Account {
  number: string;
  kind: string;
  kind_label: string;
  currency: string;
  status: string;
  status_label: string;
  balance: string;
  available_balance: string;
  accrued_interest: string;
  opened_at: string;
  savings_rate: SavingsRate | null;
}
export interface AccountsResponse {
  accounts: Account[];
  savings_rates: SavingsRate[];
}
export const getAccounts = () => apiGet<AccountsResponse>("/api/v1/banking/accounts/", true);
export const getAccount = (number: string) =>
  apiGet<Account>(`/api/v1/banking/accounts/${number}/`, true);
export const openAccount = (currency: string) =>
  apiPost<Account>("/api/v1/banking/accounts/", { currency }, true);

// --- Banca: historial --------------------------------------------------

export interface Movement {
  operation_code: string;
  kind: string;
  kind_label: string;
  direction: "debit" | "credit";
  amount: string;
  currency: string;
  balance_after: string | null;
  counterpart: string | null;
  concept: string;
  status: string;
  exchange_rate: string | null;
  created_at: string;
  has_receipt: boolean;
}
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
export function getMovements(
  number: string,
  filters: { page: number; date_from?: string; date_to?: string },
) {
  const params = new URLSearchParams({ page: String(filters.page) });
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  return apiGet<Paginated<Movement>>(
    `/api/v1/banking/accounts/${number}/transactions/?${params}`,
    true,
  );
}

// --- Banca: transferencias y conversión ----------------------------

export interface Operation {
  operation_code: string;
  kind: string;
  kind_label: string;
  status: string;
  amount: string;
  fee: string;
  currency: string;
  exchange_rate: string | null;
  destination_amount: string | null;
  destination_currency: string | null;
  source_balance_after: string;
  destination_balance_after: string | null;
  completed_at: string;
}
export interface OwnTransferPayload {
  source_number: string;
  destination_number: string;
  amount: string;
  concept?: string;
}
export const transferOwn = (payload: OwnTransferPayload) =>
  apiPost<Operation>("/api/v1/banking/transfers/own/", payload, true);
export const convertCurrency = (payload: OwnTransferPayload) =>
  apiPost<Operation>("/api/v1/banking/exchange/", payload, true);

export interface ThirdPartyPayload {
  source_number: string;
  destination_cci: string;
  amount: string;
  concept?: string;
  holder?: string;
  bank?: string;
  totp?: string;
}
export const transferThirdParty = (payload: ThirdPartyPayload) =>
  apiPost<Operation>("/api/v1/banking/transfers/third-party/", payload, true);

export interface ExchangeQuote {
  amount: string;
  from_currency: string;
  to_currency: string;
  credited: string;
  applied_rate: string;
  buy: string;
  sell: string;
  date: string;
  source: string;
}
export function getExchangeQuote(amount: string, fromCurrency: string, toCurrency: string) {
  const params = new URLSearchParams({
    amount,
    from_currency: fromCurrency,
    to_currency: toCurrency,
  });
  return apiGet<ExchangeQuote>(`/api/v1/banking/exchange/quote/?${params}`, true);
}

export async function downloadReceipt(code: string): Promise<void> {
  const res = await send("GET", `/api/v1/banking/transactions/${code}/receipt/`, undefined, true);
  if (!res.ok) throw new ApiError(res.status, null);
  const url = URL.createObjectURL(await res.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = `comprobante-${code}.pdf`;
  link.click();
  URL.revokeObjectURL(url);
}
