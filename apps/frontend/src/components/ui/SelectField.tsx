import type { ComponentProps } from "react";
import { useId } from "react";

type Props = ComponentProps<"select"> & { label: string };

export function SelectField({ label, children, className = "", ...props }: Props) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium text-white/90">
        {label}
      </label>
      <select
        id={id}
        className={
          "rounded-lg border border-white/15 bg-charcoal px-3 py-2.5 text-sm text-white outline-none " +
          "transition focus:border-cyan " +
          className
        }
        {...props}
      >
        {children}
      </select>
    </div>
  );
}
