import { useState } from "react";
import { ButtonLink } from "@/components/ui/Button";
import { QrCode } from "@/components/ui/QrCode";
import type { RegistroResponse } from "@/lib/api";

export function StepListo({ result }: { result: RegistroResponse }) {
  const [showSecret, setShowSecret] = useState(false);

  return (
    <div className="flex flex-col gap-5 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-cyan/20 text-2xl">
        ✓
      </div>
      <div>
        <h2 className="text-xl font-bold text-white">¡Cuenta creada!</h2>
        <p className="mt-1 text-sm text-white/70">Bienvenid@, {result.full_name}.</p>
      </div>

      <div className="rounded-xl bg-white/[0.04] p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-cyan">
          Tu número de cuenta
        </p>
        <p className="mt-1 font-mono text-lg font-bold tracking-wider text-white">
          {result.account_number}
        </p>
      </div>

      <div className="rounded-xl border border-white/10 p-4 text-left">
        <p className="text-sm font-semibold text-white">Método de acceso alterno (TOTP)</p>
        <p className="mt-1 text-xs text-white/60">
          Si el reconocimiento facial falla, entrarás con correo, contraseña y un código de tu app de
          autenticación. Escanéalo ahora:
        </p>
        <QrCode
          value={result.totp.otpauth_uri}
          className="mx-auto my-3 w-44 rounded-lg bg-white p-2"
        />
        <button
          type="button"
          className="text-xs text-cyan underline"
          onClick={() => setShowSecret((v) => !v)}
        >
          {showSecret ? "Ocultar" : "Mostrar"} clave manual
        </button>
        {showSecret && (
          <p className="mt-1 break-all font-mono text-xs text-white/80">{result.totp.secret}</p>
        )}
      </div>

      <ButtonLink to="/login" size="lg">
        Ir a Banca por Internet
      </ButtonLink>
    </div>
  );
}
