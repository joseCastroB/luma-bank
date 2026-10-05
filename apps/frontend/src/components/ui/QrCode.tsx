import { useMemo } from "react";
import qrcode from "qrcode-generator";

/**
 * Genera el QR en el navegador (SVG, con zona de silencio). El contenido
 * —incluido el secreto TOTP— nunca sale del dispositivo.
 */
export function QrCode({
  value,
  size = 192,
  className = "",
}: {
  value: string;
  size?: number;
  className?: string;
}) {
  const svg = useMemo(() => {
    const qr = qrcode(0, "M");
    qr.addData(value);
    qr.make();
    const count = qr.getModuleCount();
    const quiet = 4; // zona de silencio estándar (módulos)
    const total = count + quiet * 2;

    let rects = "";
    for (let r = 0; r < count; r++) {
      for (let c = 0; c < count; c++) {
        if (qr.isDark(r, c)) {
          rects += `<rect x="${c + quiet}" y="${r + quiet}" width="1" height="1"/>`;
        }
      }
    }
    return (
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${total} ${total}" ` +
      `width="100%" height="100%" preserveAspectRatio="xMidYMid meet" shape-rendering="crispEdges">` +
      `<rect width="${total}" height="${total}" fill="#fff"/>` +
      `<g fill="#0b0b0c">${rects}</g></svg>`
    );
  }, [value]);

  return (
    <div
      className={`mx-auto aspect-square rounded-xl bg-white p-3 ${className}`}
      style={{ width: size }}
      role="img"
      aria-label="Código QR para configurar TOTP"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
