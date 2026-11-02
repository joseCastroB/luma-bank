# syntax=docker/dockerfile:1
# Luma Bank - MinIO y su cliente (mc), compilados desde el código fuente oficial.
# minio/minio y minio/mc ya no existen en Docker Hub. Ver nota (1) de /VERSIONS.md.

FROM golang:1.24-alpine AS build
ARG MINIO_TAG=RELEASE.2025-09-07T16-13-09Z
ARG MINIO_COMMIT=07c3a429bfed433e49018cb0f78a52145d4bedeb
ARG MINIO_FECHA=2025-09-07T16:13:09Z
ARG MC_TAG=RELEASE.2025-08-13T08-35-41Z
ARG MC_COMMIT=7394ce0dd2a80935aded936b09fa12cbb3cb8096
ARG MC_FECHA=2025-08-13T08:35:41Z
ENV CGO_ENABLED=0
RUN apk add --no-cache git

# El commit se comprueba porque un tag de git puede moverse.
WORKDIR /src/minio
RUN git clone --depth 1 --branch "$MINIO_TAG" https://github.com/minio/minio.git . \
    && test "$(git rev-parse HEAD)" = "$MINIO_COMMIT" \
    && MINIO_RELEASE=RELEASE go build -tags kqueue -trimpath \
        -ldflags "$(MINIO_RELEASE=RELEASE go run buildscripts/gen-ldflags.go "$MINIO_FECHA")" \
        -o /out/minio

WORKDIR /src/mc
RUN git clone --depth 1 --branch "$MC_TAG" https://github.com/minio/mc.git . \
    && test "$(git rev-parse HEAD)" = "$MC_COMMIT" \
    && MC_RELEASE=RELEASE go build -tags kqueue -trimpath \
        -ldflags "$(MC_RELEASE=RELEASE go run buildscripts/gen-ldflags.go "$MC_FECHA")" \
        -o /out/mc

FROM alpine:3.22
RUN apk add --no-cache ca-certificates
COPY --from=build /out/minio /out/mc /usr/local/bin/
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
