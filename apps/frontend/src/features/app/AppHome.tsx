import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";
import { ApiError, getMe, type Me } from "@/lib/api";
import { clearSession } from "@/lib/auth";

export function AppHome() {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) {
          clearSession();
          navigate("/login", { replace: true });
          return;
        }
        setError("No se pudo cargar tu información.");
      });
  }, [navigate]);

  function logout() {
    clearSession();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-champagne-200">
      <header className="bg-rich-black text-champagne">
        <Container className="flex h-16 items-center justify-between">
          <Logo />
          <button onClick={logout} className="text-sm text-opal hover:text-champagne">
            Cerrar sesión
          </button>
        </Container>
      </header>

      <Container className="py-10">
        {error && <Alert tone="error">{error}</Alert>}
        {!me && !error && <p className="text-rich-black/60">Cargando…</p>}
        {me && (
          <>
            <h1 className="text-2xl font-bold text-rich-black">Hola, {me.full_name}</h1>
            <p className="text-sm text-rich-black/60">{me.email}</p>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {me.accounts.map((a) => (
                <div key={a.number} className="rounded-2xl border border-opal/60 bg-white p-5">
                  <p className="text-xs font-semibold uppercase tracking-wide text-seaweed">
                    Cuenta {a.currency}
                  </p>
                  <p className="mt-1 font-mono text-sm tracking-wider text-rich-black">{a.number}</p>
                  <p className="mt-3 text-2xl font-bold text-rich-black">
                    {a.currency} {Number(a.balance).toFixed(2)}
                  </p>
                  <p className="mt-1 text-xs text-rich-black/50">Estado: {a.status}</p>
                </div>
              ))}
            </div>

            <Button variant="secondary" className="mt-8" onClick={() => navigate("/")}>
              Ir al inicio
            </Button>
          </>
        )}
      </Container>
    </div>
  );
}
