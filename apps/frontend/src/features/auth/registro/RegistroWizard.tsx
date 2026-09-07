import { lazy, Suspense, useCallback, useState } from "react";
import { Stepper } from "@/components/ui/Stepper";
import type { DniValidation, RegistroResponse } from "@/lib/api";
import { StepConfirmar } from "./steps/StepConfirmar";
import { StepDatos } from "./steps/StepDatos";
import { StepDni } from "./steps/StepDni";
import { StepListo } from "./steps/StepListo";

// Los modelos de reconocimiento facial pesan varios MB: se cargan solo al llegar
// al paso de la prueba de vida.
const StepRostro = lazy(() =>
  import("./steps/StepRostro").then((m) => ({ default: m.StepRostro })),
);

export interface WizardData {
  dni: string;
  identity: DniValidation | null;
  email: string;
  birthDate: string;
  password: string;
  liveness: { passed: boolean; checks: string[] } | null;
  descriptor: number[] | null;
  descriptorAlgorithm: string;
}

const EMPTY: WizardData = {
  dni: "",
  identity: null,
  email: "",
  birthDate: "",
  password: "",
  liveness: null,
  descriptor: null,
  descriptorAlgorithm: "",
};

const STEP_LABELS = ["DNI", "Identidad", "Tus datos", "Prueba de vida", "Listo"];

export function RegistroWizard() {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<WizardData>(EMPTY);
  const [result, setResult] = useState<RegistroResponse | null>(null);

  const update = useCallback(
    (patch: Partial<WizardData>) => setData((d) => ({ ...d, ...patch })),
    [],
  );
  const next = useCallback(() => setStep((s) => Math.min(s + 1, STEP_LABELS.length - 1)), []);
  const back = useCallback(() => setStep((s) => Math.max(s - 1, 0)), []);

  return (
    <div className="rounded-2xl border border-opal/60 bg-white p-6 sm:p-8">
      <h1 className="mb-1 text-2xl font-bold text-rich-black">Abrir cuenta</h1>
      <p className="mb-6 text-sm text-rich-black/60">
        Sin ir a una agencia. Necesitas tu DNI y unos segundos frente a la cámara.
      </p>

      <Stepper steps={STEP_LABELS} current={step} />

      {step === 0 && <StepDni data={data} update={update} next={next} />}
      {step === 1 && <StepConfirmar data={data} next={next} back={back} />}
      {step === 2 && <StepDatos data={data} update={update} next={next} back={back} />}
      {step === 3 && (
        <Suspense fallback={<p className="text-sm text-rich-black/60">Cargando cámara…</p>}>
          <StepRostro
            data={data}
            update={update}
            back={back}
            onRegistered={(r) => {
              setResult(r);
              next();
            }}
          />
        </Suspense>
      )}
      {step === 4 && result && <StepListo result={result} />}
    </div>
  );
}
