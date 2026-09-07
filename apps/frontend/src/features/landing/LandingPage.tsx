import { Link } from "react-router-dom";
import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { CardArt } from "./components/CardArt";

export function LandingPage() {
  return (
    <>
      <Hero />
      <QueNecesitasHoy />
      <Producto />
      <ComoFunciona />
      <CtaFinal />
    </>
  );
}

/* ------------------------------------------------------------------ */

function Hero() {
  return (
    <section className="relative overflow-hidden bg-charcoal text-white">
      <div className="pointer-events-none absolute -right-40 -top-40 h-96 w-96 rounded-full bg-cyan/20 blur-3xl" />
      <Container className="relative grid items-center gap-12 py-20 sm:py-28 lg:grid-cols-2">
        <div>
          <p className="mb-5 inline-block rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-cyan">
            Banca 100% digital
          </p>
          <h1 className="text-5xl font-extrabold leading-[1.03] tracking-tight sm:text-6xl">
            Tu dinero,
            <br />
            <span className="text-cyan">a un vistazo.</span>
          </h1>
          <p className="mt-6 max-w-lg text-lg text-white/65">
            Abre tu cuenta en minutos con tu DNI y una prueba de vida. Entra a la Banca por Internet
            sin contraseñas: solo mírate.
          </p>
          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <ButtonLink to="/registro" size="lg" variant="primary">
              Abrir cuenta
            </ButtonLink>
            <ButtonLink to="/login" size="lg" variant="secondary">
              Banca por Internet
            </ButtonLink>
          </div>
          <p className="mt-5 text-sm text-white/40">
            Identidad validada con RENIEC · Sin costo de apertura ni mantenimiento
          </p>
        </div>
        <div className="mx-auto w-full max-w-md">
          <CardArt />
        </div>
      </Container>
    </section>
  );
}

/* ------------------------------------------------------------------ */

type Accion = {
  titulo: string;
  detalle: string;
  to?: string;
  pronto?: boolean;
};

const acciones: Accion[] = [
  { titulo: "Abrir una cuenta", detalle: "Sin ir a una agencia, en minutos.", to: "/registro" },
  { titulo: "Entrar a mi banca", detalle: "Ingresa con tu rostro.", to: "/login" },
  { titulo: "Revisar mis movimientos", detalle: "Saldos y cuentas al día.", to: "/login" },
  { titulo: "Transferir dinero", detalle: "A cualquier cuenta del país.", pronto: true },
  { titulo: "Pagar servicios", detalle: "Luz, agua, internet y más.", pronto: true },
  { titulo: "Pedir mi tarjeta", detalle: "Débito digital al instante.", pronto: true },
];

function QueNecesitasHoy() {
  return (
    <section id="hoy" className="bg-ink py-20 text-white sm:py-28">
      <Container>
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          ¿Qué necesitas hacer hoy?
        </h2>
        <p className="mt-3 max-w-2xl text-white/60">Entra directo a lo que viniste a hacer.</p>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {acciones.map((a) => (
            <AccionCard key={a.titulo} accion={a} />
          ))}
        </div>
      </Container>
    </section>
  );
}

function AccionCard({ accion }: { accion: Accion }) {
  const inner = (
    <>
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-lg font-semibold text-white">{accion.titulo}</h3>
        {accion.pronto ? (
          <span className="shrink-0 rounded-full bg-white/10 px-2 py-0.5 text-[11px] font-semibold text-white/50">
            Pronto
          </span>
        ) : (
          <span aria-hidden className="text-cyan transition group-hover:translate-x-0.5">
            →
          </span>
        )}
      </div>
      <p className="mt-2 text-sm text-white/55">{accion.detalle}</p>
    </>
  );

  const base = "group rounded-2xl border border-white/10 bg-white/[0.03] p-6 transition";

  if (accion.pronto || !accion.to) {
    return <div className={`${base} opacity-60`}>{inner}</div>;
  }
  return (
    <Link
      to={accion.to}
      className={`${base} hover:-translate-y-0.5 hover:border-cyan/50 hover:bg-white/[0.06]`}
    >
      {inner}
    </Link>
  );
}

/* ------------------------------------------------------------------ */

const features = [
  {
    title: "Sin agencias",
    body: "Todo el proceso de apertura es en línea. Recibes tu número de cuenta al terminar el registro.",
  },
  {
    title: "Acceso con tu rostro",
    body: "El login compara tu rostro en vivo con tu identidad. Método alterno con clave + código cuando lo necesites.",
  },
  {
    title: "Tu foto no se guarda",
    body: "Convertimos tu rostro en una huella numérica cifrada. Ni siquiera nosotros podemos reconstruir tu imagen.",
  },
];

function Producto() {
  return (
    <section id="producto" className="bg-charcoal py-20 text-white sm:py-28">
      <Container>
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Una cuenta pensada para el celular
        </h2>
        <p className="mt-3 max-w-2xl text-white/60">
          Luma Bank reemplaza el trámite presencial por un flujo digital verificado de punta a punta.
        </p>
        <div className="mt-12 grid gap-10 sm:grid-cols-3">
          {features.map((f) => (
            <div key={f.title}>
              <div className="mb-4 h-px w-12 bg-cyan" />
              <h3 className="text-xl font-bold text-white">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/60">{f.body}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}

/* ------------------------------------------------------------------ */

const steps = [
  {
    n: "01",
    title: "Ingresa tu DNI",
    body: "Validamos tu identidad contra RENIEC y te mostramos tus datos para que confirmes que eres tú.",
  },
  {
    n: "02",
    title: "Prueba de vida",
    body: "Una breve verificación facial (parpadeo y giro de cabeza) confirma que eres una persona real.",
  },
  {
    n: "03",
    title: "Recibe tu cuenta",
    body: "Generamos tu número de cuenta al instante. Ya puedes ingresar a la Banca por Internet.",
  },
];

function ComoFunciona() {
  return (
    <section id="como-funciona" className="bg-ink py-20 text-white sm:py-28">
      <Container>
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          Cómo funciona la apertura
        </h2>
        <div className="mt-12 grid gap-6 sm:grid-cols-3">
          {steps.map((s) => (
            <div key={s.n} className="rounded-2xl border border-white/10 bg-white/[0.03] p-6">
              <span className="text-sm font-bold text-cyan">{s.n}</span>
              <h3 className="mt-2 text-lg font-semibold text-white">{s.title}</h3>
              <p className="mt-2 text-sm text-white/60">{s.body}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}

/* ------------------------------------------------------------------ */

function CtaFinal() {
  return (
    <section className="bg-charcoal">
      <Container className="py-16 sm:py-24">
        <div className="relative overflow-hidden rounded-3xl border border-cyan/20 bg-gradient-to-br from-cyan/15 to-transparent p-10 text-center sm:p-16">
          <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Tu banco, listo en lo que dura un café.
          </h2>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <ButtonLink to="/registro" size="lg" variant="primary">
              Abrir cuenta
            </ButtonLink>
            <ButtonLink to="/login" size="lg" variant="secondary">
              Ya tengo cuenta
            </ButtonLink>
          </div>
        </div>
      </Container>
    </section>
  );
}
