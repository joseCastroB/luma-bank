/** Sesión del cliente: guarda el JWT en localStorage (por dispositivo). */

const ACCESS = "luma.access";
const REFRESH = "luma.refresh";
const ACTIVITY = "luma.lastActivity";

export interface SessionUser {
  email: string;
  full_name: string;
  dni: string | null;
}

export function setSession(access: string, refresh: string): void {
  try {
    localStorage.setItem(ACCESS, access);
    localStorage.setItem(REFRESH, refresh);
    localStorage.setItem(ACTIVITY, String(Date.now()));
  } catch {
    /* modo privado / almacenamiento bloqueado */
  }
}

/** Renueva los tokens sin contar como actividad del usuario. */
export function updateTokens(access: string, refresh: string): void {
  try {
    localStorage.setItem(ACCESS, access);
    localStorage.setItem(REFRESH, refresh);
  } catch {
    /* noop */
  }
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH);
  } catch {
    return null;
  }
}

/** La última actividad se comparte entre pestañas: una activa mantiene viva la sesión. */
export function markActivity(): void {
  try {
    localStorage.setItem(ACTIVITY, String(Date.now()));
  } catch {
    /* noop */
  }
}

export function getLastActivity(): number {
  try {
    return Number(localStorage.getItem(ACTIVITY) ?? 0);
  } catch {
    return 0;
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
    localStorage.removeItem(ACTIVITY);
  } catch {
    /* noop */
  }
}

export function isAuthenticated(): boolean {
  return Boolean(getAccessToken());
}
