import { useCallback } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";
import { useIdleLogout, type SessionEnd } from "@/features/app/useIdleLogout";
import { clearSession } from "@/lib/auth";

const LINKS = [
  { to: "/app", label: "Inicio", end: true },
  { to: "/app/transferir", label: "Transferir", end: false },
  { to: "/app/convertir", label: "Convertir", end: false },
];

/** Área privada: navegación y cierre de sesión por inactividad. */
export function AppLayout() {
  const navigate = useNavigate();

  const endSession = useCallback(
    (reason?: SessionEnd) => {
      clearSession();
      navigate("/login", { replace: true, state: reason ? { reason } : undefined });
    },
    [navigate],
  );
  const { secondsLeft, stayActive } = useIdleLogout(endSession);

  return (
    <div className="min-h-screen bg-charcoal">
      <header className="border-b border-white/10 bg-charcoal text-white">
        <Container className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 py-4">
          <Logo />
          <nav className="order-last flex w-full gap-1 sm:order-none sm:w-auto" aria-label="Principal">
            {LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  "rounded-full px-3 py-1.5 text-sm transition " +
                  (isActive ? "bg-cyan/15 text-cyan" : "text-white/60 hover:text-white")
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
          <button onClick={() => endSession()} className="text-sm text-white/50 hover:text-white">
            Cerrar sesión
          </button>
        </Container>
      </header>

      <Container className="py-8">
        <Outlet />
      </Container>

      {secondsLeft !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/70 p-4">
          <div
            role="alertdialog"
            aria-labelledby="idle-title"
            className="w-full max-w-sm rounded-2xl border border-white/15 bg-charcoal p-6"
          >
            <h2 id="idle-title" className="text-lg font-bold text-white">
              ¿Sigues ahí?
            </h2>
            <p className="mt-2 text-sm text-white/70">
              Por tu seguridad, cerraremos tu sesión en{" "}
              <strong className="text-cyan">{secondsLeft} segundos</strong> por inactividad.
            </p>
            <Button className="mt-5 w-full" onClick={stayActive}>
              Seguir conectado
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
