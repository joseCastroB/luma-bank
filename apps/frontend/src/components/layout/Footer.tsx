import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";

export function Footer() {
  return (
    <footer className="border-t border-white/5 bg-ink text-white/50">
      <Container className="flex flex-col gap-4 py-10 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-white">
          <Logo />
        </span>
        <p className="text-sm">© {new Date().getFullYear()} Luma Bank.</p>
      </Container>
    </footer>
  );
}
