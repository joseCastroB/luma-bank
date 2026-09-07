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
                  ? "bg-seaweed text-white"
                  : state === "active"
                    ? "bg-green-sheen text-rich-black"
                    : "bg-opal/40 text-rich-black/50")
              }
            >
              {state === "done" ? "✓" : i + 1}
            </span>
            <span className="hidden text-[11px] text-rich-black/60 sm:block">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
