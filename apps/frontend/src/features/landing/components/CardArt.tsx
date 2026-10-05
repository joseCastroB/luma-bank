/** Visual del hero: tarjeta Luma flotando, en la paleta de marca. */
export function CardArt() {
  return (
    <svg viewBox="0 0 420 320" className="w-full" role="img" aria-label="Tarjeta Luma Bank">
      <defs>
        <linearGradient id="luma-card" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#9ae5f3" />
          <stop offset="1" stopColor="#60d4ea" />
        </linearGradient>
        <filter id="luma-glow" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="18" result="b" />
          <feColorMatrix
            in="b"
            type="matrix"
            values="0 0 0 0 0.376  0 0 0 0 0.831  0 0 0 0 0.918  0 0 0 0.45 0"
          />
        </filter>
      </defs>

      {/* tarjeta trasera */}
      <g transform="rotate(-9 210 160)">
        <rect x="70" y="70" width="280" height="180" rx="22" fill="#373739" />
      </g>

      {/* resplandor + tarjeta principal */}
      <g transform="rotate(7 210 160)">
        <rect x="55" y="60" width="300" height="196" rx="24" filter="url(#luma-glow)" fill="#60d4ea" />
        <rect x="55" y="60" width="300" height="196" rx="24" fill="url(#luma-card)" />
        {/* chip */}
        <rect x="82" y="150" width="52" height="40" rx="8" fill="#19191a" opacity="0.85" />
        {/* franja superior */}
        <rect x="82" y="92" width="150" height="12" rx="6" fill="#19191a" opacity="0.35" />
        {/* número */}
        <g fill="#19191a" opacity="0.7">
          <rect x="82" y="212" width="46" height="12" rx="6" />
          <rect x="140" y="212" width="46" height="12" rx="6" />
          <rect x="198" y="212" width="46" height="12" rx="6" />
          <rect x="256" y="212" width="46" height="12" rx="6" />
        </g>
        {/* marca */}
        <circle cx="300" cy="100" r="16" fill="#19191a" opacity="0.75" />
        <circle cx="300" cy="100" r="7" fill="#9ae5f3" />
      </g>
    </svg>
  );
}
