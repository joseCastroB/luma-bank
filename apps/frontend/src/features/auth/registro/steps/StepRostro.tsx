import { useCallback, useEffect, useRef, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ApiError, registrar, type RegistroResponse } from "@/lib/api";
import type { WizardData } from "../RegistroWizard";
import { DESCRIPTOR_ALGORITHM, extractDescriptor, loadFaceModels } from "../face";
import { createLivenessDetector, type LivenessState } from "../liveness";
import { useCamera } from "../useCamera";

interface Props {
  data: WizardData;
  update: (patch: Partial<WizardData>) => void;
  back: () => void;
  onRegistered: (r: RegistroResponse) => void;
}

type Phase = "checking" | "captured" | "submitting" | "failed";

export function StepRostro({ data, update, back, onRegistered }: Props) {
  const { videoRef, state: camState, message: camMessage } = useCamera(true);
  const detectorRef = useRef(createLivenessDetector());
  const [live, setLive] = useState<LivenessState | null>(null);
  const [phase, setPhase] = useState<Phase>("checking");
  const [error, setError] = useState<string | null>(null);
  const [modelError, setModelError] = useState(false);

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
      update({
        descriptor: res.descriptor,
        descriptorAlgorithm: DESCRIPTOR_ALGORITHM,
        liveness: { passed: true, checks: ["blink", "head_turn"] },
      });
      setPhase("captured");
    } catch {
      setModelError(true);
    }
  }, [update, videoRef]);

  // Precarga de los pesos de face-api mientras el usuario habilita la cámara.
  useEffect(() => {
    loadFaceModels().catch(() => setModelError(true));
  }, []);

  // Bucle de prueba de vida.
  useEffect(() => {
    if (camState !== "ready" || phase !== "checking") return;
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
  }, [camState, phase, capture, videoRef]);

  function simulate() {
    // Solo desarrollo: descriptor determinista + vivacidad superada.
    const fake = Array.from({ length: 128 }, (_, i) => Math.sin(i * 0.3) * 0.5);
    update({
      descriptor: fake,
      descriptorAlgorithm: "simulado (dev)",
      liveness: { passed: true, checks: ["blink", "head_turn"] },
    });
    setPhase("captured");
  }

  async function submit() {
    if (!data.identity || !data.descriptor || !data.liveness) return;
    setPhase("submitting");
    setError(null);
    try {
      const result = await registrar({
        dni: data.identity.dni,
        identity_confirmed: true,
        birth_date: data.birthDate,
        email: data.email,
        password: data.password,
        liveness: data.liveness,
        face_descriptor: data.descriptor,
        descriptor_algorithm: data.descriptorAlgorithm || DESCRIPTOR_ALGORITHM,
      });
      onRegistered(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar el registro.");
      setPhase("failed");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="relative overflow-hidden rounded-xl bg-rich-black">
        <video
          ref={videoRef}
          playsInline
          muted
          className="aspect-[4/3] w-full -scale-x-100 object-cover"
        />
        <div className="absolute inset-x-0 bottom-0 bg-black/50 p-2 text-center text-xs text-champagne">
          {phase === "captured"
            ? "Rostro capturado ✓"
            : camState === "denied" || camState === "error"
              ? camMessage
              : camState !== "ready"
                ? "Habilitando cámara…"
                : (live?.hint ?? "Mira a la cámara")}
        </div>
      </div>

      <div className="flex gap-2 text-xs">
        <Badge on={live?.checks.includes("blink") || phase === "captured"}>Parpadeo</Badge>
        <Badge on={live?.checks.includes("head_turn") || phase === "captured"}>Giro de cabeza</Badge>
      </div>

      {modelError && (
        <Alert tone="error">
          No se pudieron cargar los modelos de reconocimiento facial. Revisa tu conexión.
        </Alert>
      )}
      {error && <Alert tone="error">{error}</Alert>}

      {phase === "captured" && (
        <Alert tone="success">Prueba de vida superada. Ya puedes crear tu cuenta.</Alert>
      )}

      <div className="mt-1 flex flex-col gap-2 sm:flex-row">
        <Button
          size="lg"
          className="sm:flex-1"
          disabled={phase !== "captured" && phase !== "failed"}
          onClick={submit}
        >
          {phase === "submitting" ? "Creando cuenta…" : "Crear mi cuenta"}
        </Button>
        <Button size="lg" variant="secondary" onClick={back} className="sm:flex-1">
          Atrás
        </Button>
      </div>

      {import.meta.env.DEV && phase !== "captured" && (
        <button
          type="button"
          onClick={simulate}
          className="self-start text-xs text-rich-black/50 underline"
        >
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
