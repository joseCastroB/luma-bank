import type { ComponentProps, ReactNode } from "react";
import { useId } from "react";

type Props = ComponentProps<"input"> & {
  label: string;
  error?: string | null;
  hint?: ReactNode;
};

export function TextField({ label, error, hint, className = "", ...props }: Props) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-white/90">
        {label}
      </label>
      <input
        id={id}
        className={
          "rounded-lg border bg-charcoal px-3 py-2.5 text-sm text-white outline-none transition " +
          "placeholder:text-white/30 focus:border-cyan " +
          (error ? "border-red-500/70" : "border-white/15") +
          " " +
          className
        }
        aria-invalid={error ? true : undefined}
        {...props}
      />
      {hint && !error && <p className="text-xs text-white/45">{hint}</p>}
      {error && <p className="text-xs font-medium text-red-400">{error}</p>}
    </div>
  );
}
