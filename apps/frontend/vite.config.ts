import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: true, // escucha en 0.0.0.0 para funcionar dentro de Docker
    port: 5173,
    strictPort: true,
    watch: {
      // el bind-mount en Docker a veces no propaga eventos de FS en Windows
      usePolling: true,
    },
  },
  preview: {
    host: true,
    port: 5173,
  },
});
