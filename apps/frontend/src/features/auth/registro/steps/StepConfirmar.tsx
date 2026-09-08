import { Button } from "@/components/ui/Button";
import type { WizardData } from "../RegistroWizard";

interface Props {
  data: WizardData;
  next: () => void;
  back: () => void;
}

export function StepConfirmar({ data, next, back }: Props) {
  const id = data.identity;
  if (!id) return null;

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
