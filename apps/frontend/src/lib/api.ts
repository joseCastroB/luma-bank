/** Cliente HTTP minimo para la API de Luma Bank. */

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { Accept: "application/json" },
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error(`GET ${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface HealthResponse {
  status: string;
  service: string;
  dni_validation_mode: string;
  debug: boolean;
  checks: Record<string, string>;
}

export const getHealth = () => apiGet<HealthResponse>("/api/health/");
