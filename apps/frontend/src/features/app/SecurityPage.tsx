import { lazy, Suspense, useEffect, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, getMe, updateBiometrics, type Me } from "@/lib/api";
import { formatDateTime } from "@/lib/money";
import { DESCRIPTOR_ALGORITHM } from "@/features/auth/shared/face";

const FaceCapture = lazy(() =>
  import("@/features/auth/shared/FaceCapture").then((m) => ({ default: m.FaceCapture })),
);

type Stage = "idle" | "capture" | "code";

/**
 * Actualización del rostro: nueva prueba de vida y luego el código TOTP.
 * El código va al final porque vence en segundos y los gestos toman su tiempo.
 */
export function SecurityPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [descriptor, setDescriptor] = useState<number[] | null>(null);
  const [totp, setTotp] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => setLoadError("No se pudo cargar tu información."));
  }, []);

  function reset() {
    setDescriptor(null);
    setTotp("");
    setError(null);
    setStage("idle");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!descriptor || totp.length < 6) return;
    setSending(true);
    setError(null);
    try {
      await updateBiometrics({
        totp,
        liveness: { passed: true, checks: ["blink", "head_turn"] },
        face_descriptor: descriptor,
        descriptor_algorithm: DESCRIPTOR_ALGORITHM,
      });
      setMe(await getMe());
      setDone(true);
      reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar tu rostro.");
      setTotp("");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="text-2xl font-bold text-white">Seguridad</h1>

      <section className="mt-6 flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
        <div>
          <h2 className="text-lg font-semibold text-white">Tu rostro</h2>
          <p className="mt-1 text-sm text-white/60">
            Actualízalo si cambió tu apariencia y te cuesta ingresar. No guardamos tu foto.
          </p>
          {me?.face_updated_at && (
            <p className="mt-2 text-xs text-white/50">Última actualización: {formatDateTime(me.face_updated_at)}</p>
          )}
        </div>

        {loadError && <Alert tone="error">{loadError}</Alert>}
        {done && <Alert tone="success">Actualizamos tu rostro. Úsalo la próxima vez que ingreses.</Alert>}

        {stage === "idle" && me && (
          <div>
            <Button
              variant="secondary"
              onClick={() => {
                setDone(false);
                setStage("capture");
              }}
            >
              Actualizar mi rostro
            </Button>
          </div>
        )}

        {stage === "capture" && (
          <Suspense fallback={<p className="text-sm text-white/60">Cargando cámara…</p>}>
            <p className="text-sm text-white/70">Parpadea y gira la cabeza para confirmar que eres tú.</p>
            <FaceCapture
              onCaptured={(captured) => {
                setDescriptor(captured);
                setStage("code");
              }}
            />
            <div>
              <Button variant="ghost" onClick={reset}>
                Cancelar
              </Button>
            </div>
          </Suspense>
        )}

        {stage === "code" && (
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <Alert tone="success">Prueba de vida completada. Falta confirmar que eres tú.</Alert>
            <TextField
              label="Código de tu app de autenticación"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="123456"
              value={totp}
              onChange={(e) => setTotp(e.target.value.replace(/\D/g, ""))}
            />
            {error && <Alert tone="error">{error}</Alert>}
            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={sending || totp.length < 6}>
                {sending ? "Guardando…" : "Guardar mi rostro"}
              </Button>
              <Button type="button" variant="ghost" onClick={reset} disabled={sending}>
                Cancelar
              </Button>
            </div>
          </form>
        )}
      </section>
    </div>
  );
}
