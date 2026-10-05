import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import type { WizardData } from "../RegistroWizard";

interface Props {
  data: WizardData;
  update: (patch: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

export function StepConfirmar({ data, update, next, back }: Props) {
  const id = data.identity;

  // Registro degradado (RNF-06): no hay datos de RENIEC, asi que el nombre lo
  // declara el usuario y se verifica a mano despues.
  if (!id) {
    return (
      <div className="flex flex-col gap-5">
        <Alert tone="warning">
          No pudimos consultar el registro oficial, así que <strong>no tenemos cómo confirmar tu
          nombre</strong> todavía. Escríbelo tal como figura en tu DNI.
        </Alert>

        <TextField
          label="Nombre completo según tu DNI"
          autoComplete="name"
          value={data.declaredFullName}
          onChange={(e) => update({ declaredFullName: e.target.value })}
          placeholder="Ana Vanesa Lancho Alvarez"
          hint="Es el mismo nombre que figura en tu documento de identidad."
        />
        <p className="text-sm text-rich-black/60">DNI {data.dni}</p>

        <div className="flex flex-col gap-2 sm:flex-row">
          <Button
            size="lg"
            className="sm:flex-1"
            disabled={data.declaredFullName.trim().split(/\s+/).length < 2}
            onClick={next}
          >
            Continuar
          </Button>
          <Button size="lg" variant="secondary" onClick={back} className="sm:flex-1">
            Corregir DNI
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-xl bg-champagne p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-seaweed">Según RENIEC</p>
        <p className="mt-1 text-lg font-bold text-rich-black">{id.nombre_completo}</p>
        <p className="text-sm text-rich-black/60">DNI {id.dni}</p>
      </div>

      <p className="text-sm text-rich-black/80">¿Eres tú?</p>

      <div className="flex flex-col gap-2 sm:flex-row">
        <Button size="lg" onClick={next} className="sm:flex-1">
          Sí, soy yo
        </Button>
        <Button size="lg" variant="secondary" onClick={back} className="sm:flex-1">
          No, corregir DNI
        </Button>
      </div>
    </div>
  );
}