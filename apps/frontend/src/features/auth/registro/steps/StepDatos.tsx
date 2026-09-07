import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import type { WizardData } from "../RegistroWizard";

interface Props {
  data: WizardData;
  update: (patch: Partial<WizardData>) => void;
  next: () => void;
  back: () => void;
}

function yearsSince(iso: string): number {
  const d = new Date(iso);
  const now = new Date();
  let age = now.getFullYear() - d.getFullYear();
  const m = now.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < d.getDate())) age--;
  return age;
}

export function StepDatos({ data, update, next, back }: Props) {
  const [email, setEmail] = useState(data.email);
  const [birthDate, setBirthDate] = useState(data.birthDate);
  const [password, setPassword] = useState(data.password);
  const [confirm, setConfirm] = useState(data.password);
  const [touched, setTouched] = useState(false);

  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const age = birthDate ? yearsSince(birthDate) : null;
  const ageOk = age !== null && age >= 18 && age < 120;
  const passOk = password.length >= 12;
  const matchOk = password === confirm;
  const formOk = emailOk && ageOk && passOk && matchOk;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!formOk) return;
    update({ email: email.trim().toLowerCase(), birthDate, password });
    next();
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <TextField
        label="Correo electrónico"
        type="email"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        hint="Lo usarás para el acceso alterno (correo + contraseña + código)."
        error={touched && !emailOk ? "Ingresa un correo válido." : null}
      />
      <TextField
        label="Fecha de nacimiento"
        type="date"
        value={birthDate}
        max={new Date().toISOString().slice(0, 10)}
        onChange={(e) => setBirthDate(e.target.value)}
        error={
          touched && birthDate && !ageOk
            ? "Debes ser mayor de 18 años para abrir una cuenta."
            : null
        }
      />
      <TextField
        label="Contraseña"
        type="password"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        hint="Mínimo 12 caracteres."
        error={touched && !passOk ? "La contraseña debe tener al menos 12 caracteres." : null}
      />
      <TextField
        label="Repite la contraseña"
        type="password"
        autoComplete="new-password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        error={touched && !matchOk ? "Las contraseñas no coinciden." : null}
      />

      <div className="mt-2 flex flex-col gap-2 sm:flex-row">
        <Button type="submit" size="lg" className="sm:flex-1" disabled={touched && !formOk}>
          Continuar
        </Button>
        <Button type="button" size="lg" variant="secondary" onClick={back} className="sm:flex-1">
          Atrás
        </Button>
      </div>
    </form>
  );
}
