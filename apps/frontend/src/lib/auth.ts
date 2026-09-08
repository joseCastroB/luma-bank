/** Sesión del cliente: guarda el JWT en localStorage (por dispositivo). */

const ACCESS = "luma.access";
const REFRESH = "luma.refresh";

export interface SessionUser {
  email: string;
  full_name: string;
  dni: string | null;
}

export function setSession(access: string, refresh: string): void {
  try {
    localStorage.setItem(ACCESS, access);
    localStorage.setItem(REFRESH, refresh);
  } catch {
    /* modo privado / almacenamiento bloqueado */
  }
}

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(ACCESS);
  } catch {
    return null;
  }
}

export function clearSession(): void {
  try {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  } catch {
    /* noop */
  }
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken());
}
