import type { ReactNode } from "react";

type Tone = "error" | "info" | "success";

const tones: Record<Tone, string> = {
  error: "border-red-300 bg-red-50 text-red-800",
  info: "border-opal bg-white text-rich-black/80",
  success: "border-green-sheen bg-green-sheen/10 text-rich-black",
};

export function Alert({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div role={tone === "error" ? "alert" : undefined} className={`rounded-lg border p-3 text-sm ${tones[tone]}`}>
      {children}
    </div>
  );
}
