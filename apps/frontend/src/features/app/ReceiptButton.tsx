import { useState } from "react";
import { downloadReceipt } from "@/lib/api";

const STYLES = {
  link: "text-xs text-cyan hover:underline disabled:opacity-50",
  button:
    "inline-flex items-center justify-center rounded-full border border-cyan/40 px-5 py-2.5 text-sm " +
    "font-semibold text-cyan transition hover:bg-cyan/10 disabled:opacity-50",
};

export function ReceiptButton({ code, variant = "link" }: { code: string; variant?: keyof typeof STYLES }) {
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");

  async function download() {
    setState("loading");
    try {
      await downloadReceipt(code);
      setState("idle");
    } catch {
      setState("error");
    }
  }

  return (
    <button type="button" onClick={download} disabled={state === "loading"} className={STYLES[variant]}>
      {state === "loading" && "Descargando…"}
      {state === "error" && "No se pudo descargar. Reintentar"}
      {state === "idle" && "Descargar comprobante"}
    </button>
  );
}
