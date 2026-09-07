import { Link } from "react-router-dom";

/**
 * HU02 - Registro y apertura de cuenta (KYC).
 * El flujo completo (DNI -> RENIEC -> prueba de vida -> cuenta) se implementa
 * en la rama feature/HU02-registro.
 */
export function RegistroPage() {
  return (
    <div className="rounded-2xl border border-opal/60 bg-white p-8">
      <h1 className="text-2xl font-bold text-rich-black">Abrir cuenta</h1>
      <p className="mt-3 text-sm text-rich-black/70">
        En construcción (HU02). Aquí irá el flujo de registro: DNI validado con RENIEC, confirmación
        de identidad, fecha de nacimiento, prueba de vida facial y generación del número de cuenta.
      </p>
      <Link to="/" className="mt-6 inline-block text-sm font-semibold text-seaweed hover:underline">
        ← Volver al inicio
      </Link>
    </div>
  );
}
