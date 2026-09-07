/** Ilustración decorativa de escaneo facial para el hero. */
export function FaceScanArt() {
  return (
    <svg viewBox="0 0 320 320" className="w-full" role="img" aria-label="Ilustración de escaneo facial">
      <defs>
        <linearGradient id="luma-scan" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#77ACA2" />
          <stop offset="1" stopColor="#468189" />
        </linearGradient>
      </defs>

      <rect x="20" y="20" width="280" height="280" rx="28" fill="#0a2b3d" />

      {/* esquinas del marco */}
      {[
        "M52 92V60h32",
        "M268 92V60h-32",
        "M52 228v32h32",
        "M268 228v32h-32",
      ].map((d) => (
        <path key={d} d={d} fill="none" stroke="#77ACA2" strokeWidth="4" strokeLinecap="round" />
      ))}

      {/* rostro estilizado */}
      <circle cx="160" cy="150" r="70" fill="none" stroke="url(#luma-scan)" strokeWidth="6" />
      <circle cx="138" cy="140" r="7" fill="#F4E9CD" />
      <circle cx="182" cy="140" r="7" fill="#F4E9CD" />
      <path
        d="M140 178c12 12 28 12 40 0"
        fill="none"
        stroke="#F4E9CD"
        strokeWidth="6"
        strokeLinecap="round"
      />

      {/* línea de escaneo */}
      <rect x="70" y="150" width="180" height="4" rx="2" fill="#F4E9CD" opacity="0.9">
        <animate attributeName="y" values="86;214;86" dur="3s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.25;0.9;0.25" dur="3s" repeatCount="indefinite" />
      </rect>
    </svg>
  );
}
