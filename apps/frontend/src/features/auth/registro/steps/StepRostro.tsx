import { useCallback, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import {
  ApiError,
  asLivenessError,
  registrar,
  type LivenessResult,
  type RegistroResponse,
} from "@/lib/api";
import { DESCRIPTOR_ALGORITHM, FaceCapture } from "../../shared/FaceCapture";
import { describePlan } from "../../shared/liveness";
import { useLivenessChallenge } from "../../shared/useLivenessChallenge";
import type { WizardData } from "../RegistroWizard";

interface Props {
  data: WizardData;
  update: (patch: Partial<WizardData>) => void;
  back: () => void;
  onRegistered: (r: RegistroResponse) => void;
}

export function StepRostro({ data, update, back, onRegistered }: Props) {
  const { challenge, loading, error: challengeError, renew } = useLivenessChallenge();
  const [ready, setReady] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function onCaptured(descriptor: number[], liveness: LivenessResult) {
    update({
      descriptor,
      descriptorAlgorithm: DESCRIPTOR_ALGORITHM,
      liveness,
    });
    setReady(true);
  }

  const submit = useCallback(
    async (liveness: LivenessResult) => {
      // Sin descriptor no hay nada que enviar. `identity` puede ser null en registro
    // degradado (RNF-06), asi que la condición correcta es sobre el descriptor.
    if (!data.descriptor) return;
      setSubmitting(true);
      setError(null);
      try {
        const result = await registrar({
          dni: data.dni,
          identity_confirmed: true,
          birth_date: data.birthDate,
          email: data.email,
          password: data.password,
          liveness,
          face_descriptor: data.descriptor,
          descriptor_algorithm: data.descriptorAlgorithm || DESCRIPTOR_ALGORITHM,
          // RNF-06: si LionAPI no tiene créditos el backend registra en modo
          // degradado y necesita el nombre declarado por el usuario. Con datos
          // oficiales manda RENIEC y este campo se ignora.
          full_name: data.identity?.nombre_completo || data.declaredFullName,
        });
        onRegistered(result);
      } catch (err) {
        setSubmitting(false);
        // Un reto rechazado se agota: hay que pedir uno nuevo, no reintentar con
        // el mismo (el backend lo borro del cache al consumirlo).
        const livenessErr = asLivenessError(err);
        if (livenessErr) {
          setReady(false);
          setError(
            `${livenessErr.message} Te pedimos una prueba nueva; no te preocupes, es normal.`,
          );
          await renew();
          return;
        }
        if (err instanceof ApiError && err.status === 409) {
          // El mismo rostro ya registrado en otra cuenta: insistir no ayuda.
          setError(err.message);
          return;
        }
        setError(err instanceof ApiError ? err.message : "No se pudo completar el registro.");
      }
    },
    [data, onRegistered, renew],
  );

  return (
    <div className="flex flex-col gap-4">
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
            Para confirmar que estás tú, hazlo en este orden:{" "}
            <strong>{describePlan(challenge.plan)}</strong>. Tienes{" "}
            {Math.round(challenge.expires_in / 60)} minutos.
          </p>
          <FaceCapture
            plan={challenge.plan}
            challengeId={challenge.challenge_id}
            onCaptured={(descriptor, liveness) => {
              onCaptured(descriptor, liveness);
              void submit(liveness);
            }}
            disabled={submitting}
          />
        </>
      )}

      {loading && !challenge && <p className="text-sm text-rich-black/60">Preparando la cámara…</p>}
      {ready && !error && !submitting && (
        <Alert tone="success">Prueba de vida superada. Ya puedes crear tu cuenta.</Alert>
      )}
      {error && <Alert tone="error">{error}</Alert>}

      <div className="mt-1 flex flex-col gap-2 sm:flex-row">
        <Button
          size="lg"
          className="sm:flex-1"
          disabled={!ready || submitting}
          onClick={() => data.liveness && void submit(data.liveness)}
        >
          {submitting ? "Creando cuenta…" : "Crear mi cuenta"}
        </Button>
        <Button size="lg" variant="secondary" onClick={back} className="sm:flex-1" disabled={submitting}>
          Atrás
        </Button>
      </div>
    </div>
  );
}