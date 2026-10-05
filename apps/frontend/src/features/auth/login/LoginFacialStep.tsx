import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ApiError, loginFacial } from "@/lib/api";
import { setSession } from "@/lib/auth";
import { FaceCapture } from "../shared/FaceCapture";

interface Props {
  identifier: string;
  onFallback: (reason: string) => void;
  onLocked: (until: string | undefined, detail: string) => void;
  onBack: () => void;
}

export function LoginFacialStep({ identifier, onFallback, onLocked, onBack }: Props) {
  const navigate = useNavigate();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);

  async function onCaptured(descriptor: number[]) {
    setSending(true);
    setError(null);
    try {
      const res = await loginFacial(identifier, descriptor, {
        passed: true,
        checks: ["blink", "head_turn"],
      });
      setSession(res.access, res.refresh);
      navigate("/app", { replace: true });
    } catch (err) {
      setSending(false);
      setAttempts((n) => n + 1);
      if (err instanceof ApiError) {
        const payload = err.payload as {
          fallback?: string;
          locked_until?: string;
          debug?: { distance: number; threshold: number };
        } | null;
        if (err.status === 423) {
          onLocked(payload?.locked_until, err.message);
          return;
        }
        if (payload?.fallback === "password_totp") {
          onFallback(err.message);
          return;
        }
        const dbg = payload?.debug
          ? ` (distancia ${payload.debug.distance} / umbral ${payload.debug.threshold})`
          : "";
        setError(err.message + dbg);
      } else {
        setError("No se pudo verificar tu rostro.");
      }
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold text-white">Verifica tu rostro</h1>
        <p className="mt-1 text-sm text-white/60">
          Parpadea y gira la cabeza. Comparamos con tu registro; tu foto no se guarda.
        </p>
      </div>

      {/* key: al fallar, remonta la cámara para un intento limpio */}
      <FaceCapture key={attempts} onCaptured={onCaptured} disabled={sending} />

      {sending && <p className="text-sm text-white/60">Verificando…</p>}
      {error && <Alert tone="error">{error}</Alert>}

      <div className="flex gap-2">
        <button type="button" onClick={onBack} className="text-sm text-cyan underline">
          ← Cambiar usuario
        </button>
        <button
          type="button"
          onClick={() => onFallback("¿Problemas con la cámara? Usa tu contraseña y código.")}
          className="ml-auto text-sm text-cyan underline"
        >
          Usar contraseña + código
        </button>
      </div>

      <Button variant="secondary" size="md" onClick={() => setAttempts((n) => n + 1)} disabled={sending}>
        Reintentar
      </Button>
    </div>
  );
}
