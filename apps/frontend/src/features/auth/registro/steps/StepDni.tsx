import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, validarDni } from "@/lib/api";
import type { WizardData } from "../RegistroWizard";

interface Props {
  data: WizardData;
  update: (patch: Partial<WizardData>) => void;
  next: () => void;
}

export function StepDni({ data, update, next }: Props) {
  const [dni, setDni] = useState(data.dni);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quota, setQuota] = useState<string | null>(null);

  // El backend hace strip() y valida 8 dígitos; aquí solo guiamos al usuario.
  const cleaned = dni.trim();
  const looksValid = /^\d{8}$/.test(cleaned);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const identity = await validarDni(cleaned);
      update({ dni: identity.dni, identity, identityPendingReview: false });
      next();
    } catch (err) {
      // RNF-06: LionAPI sin créditos responde 202, que NO es un rechazo del DNI.
      // Se deja pasar el registro en modo degradado: el nombre oficial no está
      // disponible, así que el usuario lo declara en el siguiente paso.
      if (err instanceof ApiError && err.status === 202) {
        setQuota(err.message);
        setDni(cleaned);
        update({ dni: cleaned, identity: null, identityPendingReview: true });
        return;
      }
      setError(err instanceof ApiError ? err.message : "No se pudo validar el DNI.");
    } finally {
      setLoading(false);
    }
  }

  function continueDegraded() {
    update({ dni: cleaned });
    next();
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <TextField
        label="Número de DNI"
        inputMode="numeric"
        autoComplete="off"
        maxLength={12}
        value={dni}
        onChange={(e) => setDni(e.target.value)}
        placeholder="12345678"
        hint="8 dígitos. Validaremos tu identidad con RENIEC."
        error={dni.length > 0 && !looksValid ? "Deben ser exactamente 8 dígitos." : null}
        disabled={Boolean(quota)}
      />

      {quota && (
        <>
          <Alert tone="warning">{quota}</Alert>
          <Alert tone="warning">
            Tu cuenta se creará igual, pero <strong>sin confirmar tu identidad</strong>: vas a
            escribir tu nombre completo tal como aparece en tu DNI y lo revisaremos a mano. Te
            avisaremos cuando tu identidad quede confirmada.
          </Alert>
          <Button type="button" size="lg" onClick={continueDegraded}>
            Continuar sin validar ahora
          </Button>
        </>
      )}

      {error && <Alert tone="error">{error}</Alert>}
      {!quota && (
        <Button type="submit" size="lg" disabled={!looksValid || loading}>
          {loading ? "Validando…" : "Continuar"}
        </Button>
      )}
    </form>
  );
}