import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHealth, type HealthResponse } from "@/lib/api";

type Status =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse }
  | { kind: "error"; message: string };

/** Pantalla interna: estado del API y sus dependencias. */
export function EstadoPage() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    getHealth()
      .then((data) => setStatus({ kind: "ok", data }))
      .catch((err: unknown) =>
        setStatus({ kind: "error", message: err instanceof Error ? err.message : "error" }),
      );
  }, []);

  return (
    <div className="rounded-2xl border border-opal/60 bg-white p-8">
      <h1 className="text-2xl font-bold text-rich-black">Estado del sistema</h1>

      <div className="mt-4">
        {status.kind === "loading" && <p className="text-rich-black/70">Consultando /api/health/…</p>}
        {status.kind === "error" && (
          <p className="text-red-700">No se pudo contactar la API: {status.message}</p>
        )}
        {status.kind === "ok" && (
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-rich-black/60">status</dt>
            <dd className="font-medium">{status.data.status}</dd>
            <dt className="text-rich-black/60">dni_validation_mode</dt>
            <dd className="font-medium">{status.data.dni_validation_mode}</dd>
            {Object.entries(status.data.checks).map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-rich-black/60">{k}</dt>
                <dd className="font-medium">{v}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <Link to="/" className="mt-6 inline-block text-sm font-semibold text-seaweed hover:underline">
        ← Volver al inicio
      </Link>
    </div>
  );
}
