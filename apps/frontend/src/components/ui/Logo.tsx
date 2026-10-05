export function Logo({ className = "", withText = true }: { className?: string; withText?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg viewBox="0 0 512 512" className="h-7 w-7" aria-hidden="true">
        <rect x="16" y="96" width="480" height="320" rx="64" fill="#60d4ea" />
        <rect x="72" y="176" width="112" height="80" rx="16" fill="#19191a" />
        <rect x="72" y="128" width="192" height="24" rx="12" fill="#19191a" />
        <rect x="248" y="336" width="192" height="24" rx="12" fill="#19191a" />
        <rect x="312" y="376" width="128" height="24" rx="12" fill="#19191a" />
      </svg>
      {withText && <span className="text-lg font-extrabold tracking-tight">Luma Bank</span>}
    </span>
  );
}
