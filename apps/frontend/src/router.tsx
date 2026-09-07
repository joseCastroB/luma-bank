import { createBrowserRouter } from "react-router-dom";
import { RootLayout } from "@/routes/RootLayout";
import { AuthLayout } from "@/routes/AuthLayout";
import { LandingPage } from "@/features/landing/LandingPage";
import { RegistroPage } from "@/features/auth/RegistroPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { EstadoPage } from "@/features/system/EstadoPage";
import { NotFoundPage } from "@/features/system/NotFoundPage";

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [{ index: true, element: <LandingPage /> }],
  },
  {
    element: <AuthLayout />,
    children: [
      { path: "registro", element: <RegistroPage /> },
      { path: "login", element: <LoginPage /> },
      { path: "estado", element: <EstadoPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
