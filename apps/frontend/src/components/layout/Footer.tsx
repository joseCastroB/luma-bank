import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";

export function Footer() {
  return (
    <footer className="bg-rich-black text-opal">
      <Container className="flex flex-col gap-4 py-10 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-champagne">
          <Logo />
        </span>
        <p className="text-sm">
          © {new Date().getFullYear()} Luma Bank. Proyecto académico — Curso Integrador II (UTP).
        </p>
      </Container>
    </footer>
  );
}
