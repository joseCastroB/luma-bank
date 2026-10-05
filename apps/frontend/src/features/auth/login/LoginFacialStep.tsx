import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ApiError, asLivenessError, loginFacial, type LivenessResult } from "@/lib/api";
import { setSession } from "@/lib/auth";
import { FaceCapture } from "../shared/FaceCapture";
import { describePlan } from "../shared/liveness";
import { useLivenessChallenge } from "../shared/useLivenessChallenge";

interface Props {
  identifier: string;
  onFallback: (reason: string) => void;
  onLocked: (until: string | undefined, detail: string) => void;
  onBack: () => void;
}

export function LoginFacialStep({ identifier, onFallback, onLocked, onBack }: Props) {
  const navigate = useNavigate();
  const { challenge, loading, error: challengeError, renew } = useLivenessChallenge();
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Sube en cada intento fallido: remonta la cámara y el detector para empezar
  // limpio, porque el detector conserva el estado de la secuencia anterior.
  const [attempts, setAttempts] = useState(0);

  async function onCaptured(descriptor: number[], liveness: LivenessResult) {
    setSending(true);
    setError(null);
    try {
      const res = await loginFacial(identifier, descriptor, liveness);
      setSession(res.access, res.refresh);
      navigate("/app", { replace: true });
    } catch (err) {
      setSending(false);

      // Reto rechazado (vencido, ya usado, orden incorrecto): el backend lo
      // consumio, asi que hay que pedir uno nuevo. NO cuenta como intento facial
      // fallido, por eso no se incrementa `attempts`.
      const livenessErr = asLivenessError(err);
      if (livenessErr) {
        setError(`${livenessErr.message} Prueba de nuevo.`);
        await renew();
        return;
      }

      setAttempts((n) => n + 1);
      if (err instanceof ApiError) {
        const payload = err.payload as { fallback?: string; locked_until?: string } | null;
        if (err.status === 423) {
          onLocked(payload?.locked_until, err.message);
          return;
        }
        if (payload?.fallback === "password_totp") {
          onFallback(err.message);
          return;
        }
        setError(err.message);
      } else {
        setError("No se pudo verificar tu rostro.");
      }
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold text-rich-black">Verifica tu rostro</h1>
        <p className="mt-1 text-sm text-rich-black/60">
          Comparamos la imagen en vivo con tu registro; tu foto no se guarda.
        </p>
      </div>

      {challengeError && !challenge && (
        <Alert tone="error">
          {challengeError}{" "}
          <button type="button" onClick={() => void renew()} className="underline">
            Reintentar
          </button>
        </Alert>
      )}

      {challenge && (
        <>
          <p className="text-sm text-rich-black/70">
            En este orden: <strong>{describePlan(challenge.plan)}</strong>.
          </p>
          {/* key: al fallar, remonta la cámara y el detector para un intento limpio */}
          <FaceCapture
            key={`${challenge.challenge_id}-${attempts}`}
            plan={challenge.plan}
            challengeId={challenge.challenge_id}
            onCaptured={onCaptured}
            disabled={sending}
          />
        </>
      )}

      {loading && !challenge && <p className="text-sm text-rich-black/60">Preparando la cámara…</p>}
      {sending && <p className="text-sm text-rich-black/60">Verificando…</p>}
      {error && <Alert tone="error">{error}</Alert>}

      <div className="flex gap-2">
        <button type="button" onClick={onBack} className="text-sm text-seaweed underline">
          ← Cambiar usuario
        </button>
        <button
          type="button"
          onClick={() => onFallback("¿Problemas con la cámara? Usa tu contraseña y código.")}
          className="ml-auto text-sm text-seaweed underline"
        >
          Usar contraseña + código
        </button>
      </div>

      <Button
        variant="secondary"
        size="md"
        onClick={() => {
          setAttempts((n) => n + 1);
          void renew();
        }}
        disabled={sending}
      >
        Reintentar
      </Button>
    </div>
  );
}