import { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { DESCRIPTOR_ALGORITHM, extractDescriptor, loadFaceModels } from "./face";
import { createLivenessDetector, describePlan, type LivenessState } from "./liveness";
import { useCamera } from "./useCamera";
import type { LivenessAction, LivenessResult } from "@/lib/api";

export { DESCRIPTOR_ALGORITHM };

interface Props {
  /** Plan que el servidor sorteó para este intento. */
  plan: LivenessAction[];
  challengeId: string;
  /** Se llama con el descriptor y la respuesta al reto, ya consumida por el cliente. */
  onCaptured: (descriptor: number[], liveness: LivenessResult) => void;
  /** Deshabilita la captura (p. ej. mientras se envía al backend). */
  disabled?: boolean;
}

/**
 * Cámara + reto de vida (MediaPipe) + extracción del descriptor (face-api).
 * Reutilizado por el registro (HU02) y el login (HU03).
 *
 * El plan NO se elige aqui: viene del servidor. Este componente solo ejecuta
 * los gestos que le pidan y devuelve la lista de los completados, en orden.
 */
export function FaceCapture({ plan, challengeId, onCaptured, disabled }: Props) {
  const { videoRef, state: camState, message: camMessage } = useCamera(true);
  // El detector nace ligado a un plan. Cambiar el reto implica uno nuevo.
  const detectorRef = useRef(createLivenessDetector(plan));
  const [live, setLive] = useState<LivenessState | null>(null);
  const [captured, setCaptured] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelError, setModelError] = useState(false);

  useEffect(() => {
    loadFaceModels().catch(() => setModelError(true));
  }, []);

  const capture = useCallback(
    async (completed: LivenessAction[]) => {
      const video = videoRef.current;
      if (!video) return;
      try {
        const res = await extractDescriptor(video);
        if (!res) {
          setError("No pudimos leer tu rostro con claridad. Acomódate y vuelve a intentar.");
          detectorRef.current.reset();
          setLive(null);
          return;
        }
        setCaptured(true);
        onCaptured(res.descriptor, { challenge_id: challengeId, completed_actions: completed });
      } catch {
        setModelError(true);
      }
    },
    [onCaptured, challengeId, videoRef],
  );

  useEffect(() => {
    if (camState !== "ready" || captured || disabled) return;
    let raf = 0;
    let stop = false;
    const detector = detectorRef.current;

    const tick = async () => {
      const video = videoRef.current;
      if (stop || !video || video.readyState < 2) {
        raf = requestAnimationFrame(tick);
        return;
      }
      try {
        const result = await detector.process(video, performance.now());
        if (stop) return;
        setLive(result);
        if (result.finished) {
          await capture(result.completed);
          return;
        }
      } catch {
        setModelError(true);
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      stop = true;
      cancelAnimationFrame(raf);
    };
  }, [camState, captured, disabled, capture, videoRef]);

  function simulate() {
    // Solo desarrollo: cumple el reto sin cámara. El backend no puede distinguir
    // esto de una ejecución real, así que este botón NUNCA debe existir fuera de
    // DEV (Vite lo elimina del bundle de producción).
    const fake = Array.from({ length: 128 }, (_, i) => Math.sin(i * 0.3) * 0.5);
    setCaptured(true);
    onCaptured(fake, { challenge_id: challengeId, completed_actions: [...plan] });
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-xl bg-rich-black">
        <video ref={videoRef} playsInline muted className="aspect-[4/3] w-full -scale-x-100 object-cover" />
        <div className="absolute inset-x-0 bottom-0 bg-black/50 p-2 text-center text-xs text-champagne">
          {captured
            ? "Rostro capturado ✓"
            : camState === "denied" || camState === "error"
              ? camMessage
              : camState !== "ready"
                ? "Habilitando cámara…"
                : (live?.hint ?? "Mira a la cámara")}
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-xs">
        {plan.map((action, i) => {
          const done = (live?.completed.length ?? 0) > i || captured;
          const active = !done && live?.currentIndex === i;
          return (
            <span
              key={action}
              className={
                "rounded-full px-2 py-1 " +
                (done
                  ? "bg-green-sheen/30 text-rich-black"
                  : active
                    ? "bg-champagne/40 text-rich-black"
                    : "bg-opal/30 text-rich-black/50")
              }
            >
              {done ? "✓ " : ""}
              {describePlan([action])}
            </span>
          );
        })}
      </div>

      {modelError && (
        <Alert tone="error">
          No se pudieron cargar los modelos de reconocimiento facial. Revisa tu conexión.
        </Alert>
      )}
      {error && <Alert tone="error">{error}</Alert>}

      {import.meta.env.DEV && !captured && (
        <button type="button" onClick={simulate} className="self-start text-xs text-rich-black/50 underline">
          Simular prueba de vida (solo desarrollo)
        </button>
      )}
    </div>
  );
}