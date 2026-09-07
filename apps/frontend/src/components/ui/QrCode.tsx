import { useMemo } from "react";
import qrcode from "qrcode-generator";

/**
 * Genera el QR en el navegador (SVG). El contenido —incluido el secreto TOTP—
 * nunca sale del dispositivo.
 */
export function QrCode({ value, size = 176, className = "" }: { value: string; size?: number; className?: string }) {
  const svg = useMemo(() => {
    const qr = qrcode(0, "M");
    qr.addData(value);
    qr.make();
    const count = qr.getModuleCount();
    const cell = size / count;
    let rects = "";
    for (let r = 0; r < count; r++) {
      for (let c = 0; c < count; c++) {
        if (qr.isDark(r, c)) {
          rects += `<rect x="${(c * cell).toFixed(2)}" y="${(r * cell).toFixed(2)}" width="${cell.toFixed(2)}" height="${cell.toFixed(2)}"/>`;
        }
      }
    }
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" width="${size}" height="${size}"><rect width="${size}" height="${size}" fill="#fff"/><g fill="#031926">${rects}</g></svg>`;
  }, [value, size]);

  return (
    <div
      className={className}
      role="img"
      aria-label="Código QR para configurar TOTP"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
