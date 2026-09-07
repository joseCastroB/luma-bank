import { Link } from "react-router-dom";

/**
 * HU03 - Login con reconocimiento facial.
 * El flujo completo (rostro en vivo vs embedding, fallback clave + TOTP,
 * bloqueos) se implementa en la rama feature/HU03-login.
 */
export function LoginPage() {
  return (
    <div className="rounded-2xl border border-opal/60 bg-white p-8">
      <h1 className="text-2xl font-bold text-rich-black">Banca por Internet</h1>
      <p className="mt-3 text-sm text-rich-black/70">
        En construcción (HU03). Aquí irá el ingreso con reconocimiento facial y el método alterno
        usuario / contraseña + código TOTP.
      </p>
      <Link to="/" className="mt-6 inline-block text-sm font-semibold text-seaweed hover:underline">
        ← Volver al inicio
      </Link>
    </div>
  );
}
