import type { ReactNode } from "react";

type Tone = "error" | "info" | "success" | "warning";

const tones: Record<Tone, string> = {
  error: "border-red-300 bg-red-50 text-red-800",
  info: "border-opal bg-white text-rich-black/80",
  success: "border-green-sheen bg-green-sheen/10 text-rich-black",
  // Aviso que no bloquea pero hay que leer: degradación por API caída, estado
  // pendiente de revisión, etc.
  warning: "border-champagne bg-champagne/25 text-rich-black/80",
};

export function Alert({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div
      // `warning` tambien se anuncia: es informacion que cambia lo que el
      // usuario puede hacer, y `status` lo marca sin romper el layout.
      role={tone === "error" ? "alert" : tone === "warning" ? "status" : undefined}
      className={`rounded-lg border p-3 text-sm ${tones[tone]}`}
    >
      {children}
    </div>
  );
}
