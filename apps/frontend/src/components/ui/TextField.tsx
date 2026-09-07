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
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-medium text-rich-black">
        {label}
      </label>
      <input
        id={id}
        className={
          "rounded-lg border bg-white px-3 py-2.5 text-sm outline-none transition " +
          "focus:border-seaweed " +
          (error ? "border-red-400" : "border-opal") +
          " " +
          className
        }
        aria-invalid={error ? true : undefined}
        {...props}
      />
      {hint && !error && <p className="text-xs text-rich-black/60">{hint}</p>}
      {error && <p className="text-xs font-medium text-red-700">{error}</p>}
    </div>
  );
}
