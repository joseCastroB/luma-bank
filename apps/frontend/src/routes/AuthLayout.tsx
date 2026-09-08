import { Link, Outlet } from "react-router-dom";
import { Container } from "@/components/ui/Container";
import { Logo } from "@/components/ui/Logo";

export function AuthLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-champagne-200">
      <header className="bg-rich-black text-champagne">
        <Container className="flex h-16 items-center">
          <Link to="/" className="text-champagne" aria-label="Luma Bank - inicio">
            <Logo />
          </Link>
        </Container>
      </header>
      <main className="flex flex-1 items-start justify-center px-4 py-10 sm:py-16">
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
