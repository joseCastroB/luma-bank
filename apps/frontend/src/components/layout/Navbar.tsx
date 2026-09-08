import { useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { Logo } from "@/components/ui/Logo";

const sections = [
  { href: "/#producto", label: "Producto" },
  { href: "/#seguridad", label: "Seguridad" },
  { href: "/#como-funciona", label: "Cómo funciona" },
];

export function Navbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-rich-black text-champagne">
      <Container className="flex h-16 items-center justify-between">
        <Link to="/" className="text-champagne" aria-label="Luma Bank - inicio">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-8 md:flex">
          {sections.map((s) => (
            <a key={s.href} href={s.href} className="text-sm text-opal transition hover:text-champagne">
              {s.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          <ButtonLink to="/login" variant="ghost" className="text-champagne hover:bg-white/10">
            Banca por Internet
          </ButtonLink>
          <ButtonLink to="/registro" variant="primary">
            Abrir cuenta
          </ButtonLink>
        </div>

        <button
          type="button"
          className="rounded-lg p-2 text-champagne md:hidden"
          aria-label="Abrir menú"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <svg viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="2">
            {open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
      </Container>

      {open && (
        <div className="border-t border-white/10 md:hidden">
          <Container className="flex flex-col gap-2 py-4">
            {sections.map((s) => (
              <a
                key={s.href}
                href={s.href}
                className="rounded-lg px-2 py-2 text-opal hover:bg-white/5"
                onClick={() => setOpen(false)}
              >
                {s.label}
              </a>
            ))}
            <NavLink to="/login" className="rounded-lg px-2 py-2 hover:bg-white/5" onClick={() => setOpen(false)}>
              Banca por Internet
            </NavLink>
            <ButtonLink to="/registro" variant="primary" className="mt-1" >
              Abrir cuenta
            </ButtonLink>
          </Container>
        </div>
      )}
    </header>
  );
}
