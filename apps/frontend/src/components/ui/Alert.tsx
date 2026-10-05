import type { ReactNode } from "react";

type Tone = "error" | "info" | "success";

const tones: Record<Tone, string> = {
  error: "border-red-500/40 bg-red-500/10 text-red-200",
  info: "border-white/15 bg-white/5 text-white/80",
  success: "border-cyan/40 bg-cyan/10 text-cyan-soft",
};

export function Alert({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div
      role={tone === "error" ? "alert" : undefined}
      className={`rounded-lg border p-3 text-sm ${tones[tone]}`}
    >
      {children}
    </div>
  );
}
