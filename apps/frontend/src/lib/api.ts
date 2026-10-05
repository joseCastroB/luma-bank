/** Cliente HTTP para la API de Luma Bank. */
import { getAccessToken } from "./auth";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  payload: unknown;
  constructor(status: number, payload: unknown) {
    super(extractMessage(payload, status));
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
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

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = false,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
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

/**
 * Respuesta 202 de RNF-06: LionAPI alcanzó su límite de consultas.
 *
 * No es un DNI inválido, así que NO debe frenar el registro. El backend acepta
 * seguir en modo degradado, pero entonces el nombre oficial no existe y lo
 * declara el usuario. Por eso vuelve sin datos de identidad.
 */
export interface DniValidationQuota {
  detail: string;
  identity_pending_review: true;
}

export const validarDni = (dni: string) =>
  apiPost<DniValidation>("/api/v1/accounts/registro/validar-dni/", { dni });

// --- Prueba de vida (RNF-15) -------------------------------------------
//
// El reto lo sortea el SERVIDOR. El cliente ya no declara `passed`: eso era una
// asercion del navegador y cualquiera podia mandarla por curl. Ahora el cliente
// pide el plan, lo ejecuta en ese orden y responde QUE GESTOS hizo; el backend
// decide si coincide con el que emitio.

export type LivenessAction = "blink" | "head_turn_left" | "head_turn_right";

export interface LivenessChallenge {
  challenge_id: string;
  plan: LivenessAction[];
  expires_in: number;
}

export interface LivenessResult {
  challenge_id: string;
  completed_actions: LivenessAction[];
}

export const requestLivenessChallenge = () =>
  apiPost<LivenessChallenge>("/api/v1/accounts/liveness/challenge/");

/**
 * Error de reto de vida (vencido, ya usado, orden incorrecto, demasiado rápido).
 * El backend lo devuelve con un `code` estable: el cliente debe pedir un reto
 * nuevo, nunca reintentar con el mismo.
 */
export class LivenessError extends Error {
  code: string;
  constructor(message: string, code: string) {
    super(message);
    this.name = "LivenessError";
    this.code = code;
  }
}

/** Traduce un ApiError del backend a LivenessError si corresponde. */
export function asLivenessError(err: unknown): LivenessError | null {
  if (!(err instanceof ApiError)) return null;
  const payload = err.payload as { code?: unknown; detail?: unknown } | null;
  if (!payload || typeof payload.code !== "string") return null;
  return new LivenessError(err.message, payload.code);
}

export interface RegistroPayload {
  dni: string;
  identity_confirmed: boolean;
  birth_date: string; // YYYY-MM-DD
  email: string;
  password: string;
  liveness: LivenessResult;
  face_descriptor: number[];
  descriptor_algorithm: string;
  /** Solo se usa en registro degradado (RNF-06) cuando LionAPI no tiene créditos. */
  full_name?: string;
}
export interface RegistroResponse {
  account_number: string;
  email: string;
  full_name: string;
  totp: { secret: string; otpauth_uri: string; issuer: string };
  message: string;
  /** true = cuenta creada SIN identidad verificada (RNF-06, requiere revisión manual). */
  identity_pending_review: boolean;
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
  liveness: LivenessResult,
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
