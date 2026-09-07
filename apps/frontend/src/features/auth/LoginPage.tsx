import { LoginFlow } from "./login/LoginFlow";

/** HU03 - Login con reconocimiento facial (+ método alterno). */
export function LoginPage() {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 sm:p-8">
      <LoginFlow />
    </div>
  );
}
