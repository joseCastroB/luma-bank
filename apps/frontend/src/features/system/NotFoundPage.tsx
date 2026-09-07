import { ButtonLink } from "@/components/ui/Button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-5xl font-extrabold text-seaweed">404</p>
      <h1 className="text-xl font-semibold text-rich-black">Esta página no existe</h1>
      <ButtonLink to="/" variant="primary">
        Ir al inicio
      </ButtonLink>
    </div>
  );
}
