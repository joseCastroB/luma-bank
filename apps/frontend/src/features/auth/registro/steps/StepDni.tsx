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

  // El backend hace strip() y valida 8 dígitos; aquí solo guiamos al usuario.
  const cleaned = dni.trim();
  const looksValid = /^\d{8}$/.test(cleaned);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const identity = await validarDni(cleaned);
      update({ dni: identity.dni, identity });
      next();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo validar el DNI.");
    } finally {
      setLoading(false);
    }
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
      />
      {error && <Alert tone="error">{error}</Alert>}
      <Button type="submit" size="lg" disabled={!looksValid || loading}>
        {loading ? "Validando…" : "Continuar"}
      </Button>
    </form>
  );
}
