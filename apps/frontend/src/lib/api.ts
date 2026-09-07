/** Cliente HTTP para la API de Luma Bank. */

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

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    credentials: "include",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

export const apiGet = <T>(path: string) => request<T>("GET", path);
export const apiPost = <T>(path: string, body?: unknown) => request<T>("POST", path, body);

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
