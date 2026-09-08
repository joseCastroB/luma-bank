import { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { DESCRIPTOR_ALGORITHM, extractDescriptor, loadFaceModels } from "./face";
import { createLivenessDetector, type LivenessState } from "./liveness";
import { useCamera } from "./useCamera";

export { DESCRIPTOR_ALGORITHM };

interface Props {
  /** Se llama con el descriptor de 128d cuando se supera la prueba de vida. */
  onCaptured: (descriptor: number[]) => void;
  /** Deshabilita la captura (p. ej. mientras se envía al backend). */
  disabled?: boolean;
}

/**
 * Cámara + prueba de vida (MediaPipe) + extracción del descriptor (face-api).
 * Reutilizado por el registro (HU02) y el login (HU03).
 */
export function FaceCapture({ onCaptured, disabled }: Props) {
  const { videoRef, state: camState, message: camMessage } = useCamera(true);
  const detectorRef = useRef(createLivenessDetector());
  const [live, setLive] = useState<LivenessState | null>(null);
  const [captured, setCaptured] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelError, setModelError] = useState(false);

  useEffect(() => {
    loadFaceModels().catch(() => setModelError(true));
  }, []);

  const capture = useCallback(async () => {
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
      onCaptured(res.descriptor);
    } catch {
      setModelError(true);
    }
  }, [onCaptured, videoRef]);

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
        if (result.passed) {
          await capture();
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
    const fake = Array.from({ length: 128 }, (_, i) => Math.sin(i * 0.3) * 0.5);
    setCaptured(true);
    onCaptured(fake);
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

      <div className="flex gap-2 text-xs">
        <Badge on={captured || live?.checks.includes("blink")}>Parpadeo</Badge>
        <Badge on={captured || live?.checks.includes("head_turn")}>Giro de cabeza</Badge>
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

function Badge({ on, children }: { on?: boolean; children: React.ReactNode }) {
  return (
    <span
      className={
        "rounded-full px-2 py-1 " +
        (on ? "bg-green-sheen/30 text-rich-black" : "bg-opal/30 text-rich-black/50")
      }
    >
      {on ? "✓ " : ""}
      {children}
    </span>
  );
}
