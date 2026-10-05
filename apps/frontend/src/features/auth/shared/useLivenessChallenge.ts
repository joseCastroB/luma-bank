/**
 * Pide el reto de vida al servidor y lo expone al componente de captura.
 *
 * Existe como hook y no como estado suelto en cada pantalla porque el reto es
 * de UN SOLO USO: si el registro o el login lo consumen, hay que pedir otro.
 * La funcion `renew` centraliza esa renovacion y es la unica forma de obtener
 * un reto nuevo, para que nadie quede usando un reto ya gastado.
 */
import { useCallback, useEffect, useState } from "react";
import { ApiError, requestLivenessChallenge, type LivenessChallenge } from "@/lib/api";

export function useLivenessChallenge() {
  const [challenge, setChallenge] = useState<LivenessChallenge | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const renew = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setChallenge(await requestLivenessChallenge());
    } catch (err) {
      setChallenge(null);
      setError(
        err instanceof ApiError
          ? err.message
          : "No pudimos iniciar la prueba de vida. Revisa tu conexión.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Se difiere a la siguiente tarea: pedir el reto sincronamente dentro del
    // efecto provocaria un render en cascada, que React 19 penaliza. El
    // setTimeout ademas da un punto de cancelacion si el componente se desmonta
    // antes de que la peticion salga.
    const timer = setTimeout(() => void renew(), 0);
    return () => clearTimeout(timer);
  }, [renew]);

  return { challenge, loading, error, renew };
}