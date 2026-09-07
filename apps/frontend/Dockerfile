# syntax=docker/dockerfile:1
# Luma Bank - Frontend (React + Vite + Tailwind)
# Build con Node 24, sirve con Nginx. Ver /VERSIONS.md

# ---------------------------------------------------------------------------
# Stage build
# ---------------------------------------------------------------------------
FROM node:24-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# La URL de la API se hornea en el bundle en tiempo de build.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---------------------------------------------------------------------------
# Stage runtime (produccion): Nginx sirve los estaticos
# ---------------------------------------------------------------------------
FROM nginx:1.30-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
