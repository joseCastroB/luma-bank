import { createBrowserRouter } from "react-router-dom";
import { RootLayout } from "@/routes/RootLayout";
import { AuthLayout } from "@/routes/AuthLayout";
import { RequireAuth } from "@/routes/RequireAuth";
import { AppLayout } from "@/routes/AppLayout";
import { LandingPage } from "@/features/landing/LandingPage";
import { RegistroPage } from "@/features/auth/RegistroPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { AppHome } from "@/features/app/AppHome";
import { AccountDetailPage } from "@/features/app/AccountDetailPage";
import { TransferPage } from "@/features/app/TransferPage";
import { ExchangePage } from "@/features/app/ExchangePage";
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
  {
    element: <RequireAuth />,
    children: [
      {
        path: "app",
        element: <AppLayout />,
        children: [
          { index: true, element: <AppHome /> },
          { path: "cuentas/:number", element: <AccountDetailPage /> },
          { path: "transferir", element: <TransferPage /> },
          { path: "convertir", element: <ExchangePage /> },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
