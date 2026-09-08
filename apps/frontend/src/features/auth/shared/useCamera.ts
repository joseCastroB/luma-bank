import { useEffect, useRef, useState } from "react";

export type CameraState = "starting" | "ready" | "denied" | "error";

/** Pide acceso a la cámara frontal y lo enlaza a un <video>. */
export function useCamera(active: boolean) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [state, setState] = useState<CameraState>("starting");
  const [message, setMessage] = useState<string>("");

  useEffect(() => {
    if (!active) return;
    let stream: MediaStream | null = null;
    let cancelled = false;

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "user", width: 640, height: 480 }, audio: false })
      .then((s) => {
        if (cancelled) {
          s.getTracks().forEach((t) => t.stop());
          return;
        }
        stream = s;
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          void videoRef.current.play();
        }
        setState("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const name = err instanceof DOMException ? err.name : "";
        if (name === "NotAllowedError" || name === "SecurityError") {
          setState("denied");
          setMessage("Necesitamos permiso para usar la cámara.");
        } else {
          setState("error");
          setMessage("No se pudo abrir la cámara. Verifica que otra app no la esté usando.");
        }
      });

    return () => {
      cancelled = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [active]);

  return { videoRef, state, message };
}
