import { lazy, Suspense, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { LoginPasswordStep } from "./LoginPasswordStep";

const LoginFacialStep = lazy(() =>
  import("./LoginFacialStep").then((m) => ({ default: m.LoginFacialStep })),
);

type Stage = "identify" | "facial" | "password" | "locked";

export function LoginFlow() {
  const [stage, setStage] = useState<Stage>("identify");
  const [identifier, setIdentifier] = useState("");
  const [reason, setReason] = useState<string>("");
  const [lockInfo, setLockInfo] = useState<{ detail: string; until?: string }>({ detail: "" });

  if (stage === "identify") {
    return (
      <IdentifyStep
        onSubmit={(id) => {
          setIdentifier(id);
          setStage("facial");
        }}
        onUsePassword={(id) => {
          setIdentifier(id);
          setReason("");
          setStage("password");
        }}
      />
    );
  }

  if (stage === "facial") {
    return (
      <Suspense fallback={<p className="text-sm text-rich-black/60">Cargando cámara…</p>}>
        <LoginFacialStep
          identifier={identifier}
          onBack={() => setStage("identify")}
          onFallback={(r) => {
            setReason(r);
            setStage("password");
          }}
          onLocked={(until, detail) => {
            setLockInfo({ detail, until });
            setStage("locked");
          }}
        />
      </Suspense>
    );
  }

  if (stage === "password") {
    return <LoginPasswordStep identifier={identifier} reason={reason} />;
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold text-rich-black">Cuenta bloqueada</h1>
      <Alert tone="error">
        {lockInfo.detail}
        {lockInfo.until && (
          <>
            {" "}
            Podrás volver a intentar el {new Date(lockInfo.until).toLocaleString("es-PE")}.
          </>
        )}
      </Alert>
      <Button variant="secondary" onClick={() => setStage("identify")}>
        Volver
      </Button>
    </div>
  );
}

function IdentifyStep({
  onSubmit,
  onUsePassword,
}: {
  onSubmit: (id: string) => void;
  onUsePassword: (id: string) => void;
}) {
  const [id, setId] = useState("");
  const ok = id.trim().length >= 3;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (ok) onSubmit(id.trim());
      }}
      className="flex flex-col gap-4"
    >
      <div>
        <h1 className="text-2xl font-bold text-rich-black">Banca por Internet</h1>
        <p className="mt-1 text-sm text-rich-black/60">Ingresa con tu rostro.</p>
      </div>
      <TextField
        label="Correo o DNI"
        autoComplete="username"
        value={id}
        onChange={(e) => setId(e.target.value)}
      />
      <Button type="submit" size="lg" disabled={!ok}>
        Continuar
      </Button>
      <button
        type="button"
        onClick={() => ok && onUsePassword(id.trim())}
        className="text-sm text-seaweed underline disabled:opacity-50"
        disabled={!ok}
      >
        Prefiero usar contraseña + código
      </button>
    </form>
  );
}
