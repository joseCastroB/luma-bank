import { useCallback, useEffect, useState } from "react";
import { refreshSession } from "@/lib/api";
import { getLastActivity, isAuthenticated, markActivity } from "@/lib/auth";

const IDLE_MS = 5 * 60 * 1000;
const WARNING_MS = 30 * 1000;
const TOKEN_RENEWAL_MS = 3 * 60 * 1000;
const ACTIVITY_EVENTS = ["mousedown", "mousemove", "keydown", "scroll", "touchstart"] as const;

export type SessionEnd = "idle" | "expired";

/**
 * Cierra la sesión tras 5 minutos sin actividad, con aviso en los últimos 30 segundos.
 * Compara marcas de tiempo en cada tic: así también funciona si el equipo se suspendió.
 * Mientras haya actividad renueva el JWT; el servidor corta a quien deja de renovarlo.
 */
export function useIdleLogout(onEnd: (reason: SessionEnd) => void) {
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);

  const stayActive = useCallback(() => {
    markActivity();
    setSecondsLeft(null);
  }, []);

  useEffect(() => {
    let lastRenewal = Date.now();

    function tick() {
      if (!isAuthenticated()) {
        onEnd("expired");
        return;
      }
      const now = Date.now();
      const remaining = IDLE_MS - (now - getLastActivity());
      if (remaining <= 0) {
        onEnd("idle");
        return;
      }
      setSecondsLeft(remaining <= WARNING_MS ? Math.ceil(remaining / 1000) : null);
      if (remaining > WARNING_MS && now - lastRenewal >= TOKEN_RENEWAL_MS) {
        lastRenewal = now;
        void refreshSession();
      }
    }

    // Con la sesión ya vencida (pestaña reabierta), la actividad no debe revivirla.
    tick();
    const interval = window.setInterval(tick, 1000);
    const onActivity = () => {
      if (getLastActivity() + IDLE_MS > Date.now()) markActivity();
    };
    for (const event of ACTIVITY_EVENTS) {
      window.addEventListener(event, onActivity, { passive: true });
    }
    return () => {
      window.clearInterval(interval);
      for (const event of ACTIVITY_EVENTS) window.removeEventListener(event, onActivity);
    };
  }, [onEnd]);

  return { secondsLeft, stayActive };
}
