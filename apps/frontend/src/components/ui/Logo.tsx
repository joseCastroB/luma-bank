export function Logo({ className = "", withText = true }: { className?: string; withText?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="currentColor" />
        <circle cx="16" cy="16" r="8" fill="none" stroke="#77ACA2" strokeWidth="2.5" />
        <circle cx="16" cy="16" r="3" fill="#F4E9CD" />
      </svg>
      {withText && <span className="text-lg font-extrabold tracking-tight">Luma Bank</span>}
    </span>
  );
}
