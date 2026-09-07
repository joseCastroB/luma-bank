import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError, loginPassword } from "@/lib/api";
import { setSession } from "@/lib/auth";

interface Props {
  identifier: string;
  reason?: string;
}

export function LoginPasswordStep({ identifier, reason }: Props) {
  const navigate = useNavigate();
  const [id, setId] = useState(identifier);
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await loginPassword(id.trim(), password, totp.trim());
      setSession(res.access, res.refresh);
      navigate("/app", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión.");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold text-rich-black">Acceso alterno</h1>
      {reason && <Alert tone="info">{reason}</Alert>}

      <TextField
        label="Correo o DNI"
        autoComplete="username"
        value={id}
        onChange={(e) => setId(e.target.value)}
      />
      <TextField
        label="Contraseña"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <TextField
        label="Código de tu app de autenticación"
        inputMode="numeric"
        autoComplete="one-time-code"
        maxLength={6}
        placeholder="123456"
        value={totp}
        onChange={(e) => setTotp(e.target.value)}
        hint="6 dígitos que cambian cada 30 segundos (TOTP)."
      />

      {error && <Alert tone="error">{error}</Alert>}

      <Button type="submit" size="lg" disabled={loading || !password || totp.length < 6}>
        {loading ? "Verificando…" : "Ingresar"}
      </Button>
    </form>
  );
}
