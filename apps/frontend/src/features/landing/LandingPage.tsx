import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { FaceScanArt } from "./components/FaceScanArt";

export function LandingPage() {
  return (
    <>
      <Hero />
      <Producto />
      <ComoFunciona />
      <Seguridad />
      <CtaFinal />
    </>
  );
}

function Hero() {
  return (
    <section className="bg-rich-black text-champagne">
      <Container className="grid items-center gap-12 py-16 sm:py-24 lg:grid-cols-2">
        <div>
          <p className="mb-4 inline-block rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-green-sheen">
            Banca 100% digital
          </p>
          <h1 className="text-4xl font-extrabold leading-tight sm:text-5xl">
            Tu banco sin filas, <span className="text-green-sheen">sin contraseñas</span> y sin
            agencias.
          </h1>
          <p className="mt-5 max-w-lg text-lg text-opal">
            Abre tu cuenta en minutos con tu DNI y una prueba de vida facial. Ingresa a la Banca por
            Internet solo mostrando tu rostro.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <ButtonLink to="/registro" size="lg" variant="primary">
              Abrir cuenta
            </ButtonLink>
            <ButtonLink
              to="/login"
              size="lg"
              variant="secondary"
              className="border-opal text-opal hover:bg-opal hover:text-rich-black"
            >
              Banca por Internet
            </ButtonLink>
          </div>
          <p className="mt-4 text-sm text-opal/80">
            Identidad validada con RENIEC. Sin costo de apertura ni mantenimiento.
          </p>
        </div>
        <div className="mx-auto w-full max-w-sm">
          <FaceScanArt />
        </div>
      </Container>
    </section>
  );
}

const features = [
  {
    title: "Sin agencias",
    body: "Todo el proceso de apertura es en línea. Tu número de cuenta al terminar el registro.",
  },
  {
    title: "Acceso con tu rostro",
    body: "El login compara tu rostro en vivo con tu identidad. Método alterno con clave + código si lo necesitas.",
  },
  {
    title: "Seguro por diseño",
    body: "Nunca guardamos tus fotos: solo una huella matemática cifrada de tu rostro.",
  },
];

function Producto() {
  return (
    <section id="producto" className="py-16 sm:py-24">
      <Container>
        <h2 className="text-3xl font-bold text-rich-black">Una cuenta pensada para el celular</h2>
        <p className="mt-3 max-w-2xl text-rich-black/70">
          Luma Bank reemplaza el trámite presencial por un flujo digital verificado.
        </p>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {features.map((f) => (
            <div key={f.title} className="rounded-2xl border border-opal/60 bg-white p-6">
              <div className="mb-4 h-10 w-10 rounded-xl bg-green-sheen/30" />
              <h3 className="text-lg font-semibold text-rich-black">{f.title}</h3>
              <p className="mt-2 text-sm text-rich-black/70">{f.body}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}

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
    <section id="como-funciona" className="bg-champagne py-16 sm:py-24">
      <Container>
        <h2 className="text-3xl font-bold text-rich-black">Cómo funciona la apertura</h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {steps.map((s) => (
            <div key={s.n} className="rounded-2xl bg-white p-6 shadow-sm">
              <span className="text-sm font-bold text-seaweed">{s.n}</span>
              <h3 className="mt-2 text-lg font-semibold text-rich-black">{s.title}</h3>
              <p className="mt-2 text-sm text-rich-black/70">{s.body}</p>
            </div>
          ))}
        </div>
      </Container>
    </section>
  );
}

const securityPoints = [
  "Guardamos un embedding facial, nunca la foto.",
  "El embedding se cifra con AES-256 antes de almacenarse.",
  "Se guarda en almacenamiento de objetos aislado (MinIO), fuera de la base de datos.",
  "Segundo factor con código temporal (TOTP) para el método alterno.",
  "Prácticas de autenticación alineadas a OWASP ASVS nivel 2.",
];

function Seguridad() {
  return (
    <section id="seguridad" className="py-16 sm:py-24">
      <Container className="grid gap-10 lg:grid-cols-2 lg:items-center">
        <div>
          <h2 className="text-3xl font-bold text-rich-black">Tu rostro no se guarda como foto</h2>
          <p className="mt-3 text-rich-black/70">
            Convertimos tu rostro en una huella numérica irreversible. Aunque alguien accediera al
            almacenamiento, no podría reconstruir tu imagen.
          </p>
        </div>
        <ul className="space-y-3">
          {securityPoints.map((p) => (
            <li key={p} className="flex gap-3 rounded-xl border border-opal/60 bg-white p-4">
              <span aria-hidden className="mt-0.5 text-green-sheen">
                ✓
              </span>
              <span className="text-sm text-rich-black/80">{p}</span>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}

function CtaFinal() {
  return (
    <section className="bg-seaweed text-white">
      <Container className="flex flex-col items-center gap-6 py-14 text-center">
        <h2 className="text-2xl font-bold sm:text-3xl">¿List@ para abrir tu cuenta?</h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <ButtonLink to="/registro" size="lg" variant="primary">
            Abrir cuenta
          </ButtonLink>
          <ButtonLink
            to="/login"
            size="lg"
            variant="secondary"
            className="border-white text-white hover:bg-white hover:text-seaweed"
          >
            Ya tengo cuenta
          </ButtonLink>
        </div>
      </Container>
    </section>
  );
}
