import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ApiError, registrar, type RegistroResponse } from "@/lib/api";
import { DESCRIPTOR_ALGORITHM, FaceCapture } from "../../shared/FaceCapture";
import type { WizardData } from "../RegistroWizard";

interface Props {
  data: WizardData;
  update: (patch: Partial<WizardData>) => void;
  back: () => void;
  onRegistered: (r: RegistroResponse) => void;
}

export function StepRostro({ data, update, back, onRegistered }: Props) {
  const [ready, setReady] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onCaptured(descriptor: number[]) {
    update({
      descriptor,
      descriptorAlgorithm: DESCRIPTOR_ALGORITHM,
      liveness: { passed: true, checks: ["blink", "head_turn"] },
    });
    setReady(true);
  }

  async function submit() {
    if (!data.identity || !data.descriptor || !data.liveness) return;
    setSubmitting(true);
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
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <FaceCapture onCaptured={onCaptured} disabled={submitting} />

      {ready && !error && (
        <Alert tone="success">Prueba de vida superada. Ya puedes crear tu cuenta.</Alert>
      )}
      {error && <Alert tone="error">{error}</Alert>}

      <div className="mt-1 flex flex-col gap-2 sm:flex-row">
        <Button size="lg" className="sm:flex-1" disabled={!ready || submitting} onClick={submit}>
          {submitting ? "Creando cuenta…" : "Crear mi cuenta"}
        </Button>
        <Button size="lg" variant="secondary" onClick={back} className="sm:flex-1" disabled={submitting}>
          Atrás
        </Button>
      </div>
    </div>
  );
}
