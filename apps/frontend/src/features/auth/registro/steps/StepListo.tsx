import { useState } from "react";
import { ButtonLink } from "@/components/ui/Button";
import type { RegistroResponse } from "@/lib/api";

/** QR del otpauth:// usando la API pública de imágenes de charts (solo lectura). */
function qrUrl(data: string): string {
  return `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(data)}`;
}

export function StepListo({ result }: { result: RegistroResponse }) {
  const [showSecret, setShowSecret] = useState(false);

  return (
    <div className="flex flex-col gap-5 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-sheen/30 text-2xl">
        ✓
      </div>
      <div>
        <h2 className="text-xl font-bold text-rich-black">¡Cuenta creada!</h2>
        <p className="mt-1 text-sm text-rich-black/70">Bienvenid@, {result.full_name}.</p>
      </div>

      <div className="rounded-xl bg-champagne p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-seaweed">
          Tu número de cuenta
        </p>
        <p className="mt-1 font-mono text-lg font-bold tracking-wider text-rich-black">
          {result.account_number}
        </p>
      </div>

      <div className="rounded-xl border border-opal/60 p-4 text-left">
        <p className="text-sm font-semibold text-rich-black">Método de acceso alterno (TOTP)</p>
        <p className="mt-1 text-xs text-rich-black/60">
          Si el reconocimiento facial falla, entrarás con correo, contraseña y un código de tu app de
          autenticación. Escanéalo ahora:
        </p>
        <img
          src={qrUrl(result.totp.otpauth_uri)}
          alt="Código QR para configurar TOTP"
          className="mx-auto my-3 h-44 w-44 rounded-lg bg-white p-2"
        />
        <button
          type="button"
          className="text-xs text-seaweed underline"
          onClick={() => setShowSecret((v) => !v)}
        >
          {showSecret ? "Ocultar" : "Mostrar"} clave manual
        </button>
        {showSecret && (
          <p className="mt-1 break-all font-mono text-xs text-rich-black/80">{result.totp.secret}</p>
        )}
      </div>

      <ButtonLink to="/login" size="lg">
        Ir a Banca por Internet
      </ButtonLink>
    </div>
  );
}
