import { useLocation } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { LoginFlow } from "./login/LoginFlow";

/** HU03 - Login con reconocimiento facial (+ método alterno). */
export function LoginPage() {
  const { state } = useLocation();
  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-6 sm:p-8">
      {state?.reason === "idle" && (
        <Alert tone="info">Cerramos tu sesión por inactividad. Ingresa de nuevo para continuar.</Alert>
      )}
      {state?.reason === "expired" && (
        <Alert tone="info">Tu sesión expiró. Ingresa de nuevo para continuar.</Alert>
      )}
      <LoginFlow />
    </div>
  );
}
