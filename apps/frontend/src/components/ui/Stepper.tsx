export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="mb-6 flex items-center gap-2">
      {steps.map((label, i) => {
        const state = i < current ? "done" : i === current ? "active" : "todo";
        return (
          <li key={label} className="flex flex-1 flex-col items-center gap-1">
            <span
              className={
                "flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold " +
                (state === "done"
                  ? "bg-cyan/25 text-cyan"
                  : state === "active"
                    ? "bg-cyan text-ink"
                    : "bg-white/10 text-white/40")
              }
            >
              {state === "done" ? "✓" : i + 1}
            </span>
            <span className="hidden text-[11px] text-white/50 sm:block">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
