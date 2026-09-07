import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "@/lib/api";

type Status = { kind: "loading" } | { kind: "ok"; data: HealthResponse } | { kind: "error"; message: string };

export default function App() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    getHealth()
      .then((data) => setStatus({ kind: "ok", data }))
      .catch((err: unknown) =>
        setStatus({ kind: "error", message: err instanceof Error ? err.message : "error" }),
      );
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="flex items-center gap-3">
        <img src="/luma.svg" alt="" className="h-10 w-10" />
        <h1 className="text-3xl font-bold text-rich-black">Luma Bank</h1>
      </div>

      <p className="text-seaweed">
        Scaffolding del Sprint 0 operativo. La landing (HU01) llega en el Sprint 1.
      </p>

      <section className="w-full rounded-xl border border-opal bg-white/60 p-5 text-left">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-seaweed">
          Estado de la API
        </h2>
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
      </section>

      <div className="flex gap-3">
        <button
          type="button"
          className="rounded-lg bg-green-sheen px-5 py-2.5 font-semibold text-rich-black transition hover:brightness-95"
        >
          Abrir cuenta
        </button>
        <button
          type="button"
          className="rounded-lg border border-seaweed px-5 py-2.5 font-semibold text-seaweed transition hover:bg-seaweed hover:text-white"
        >
          Banca por Internet
        </button>
      </div>
    </main>
  );
}
