/**
 * URLs de los modelos de ML. Por defecto se cargan desde jsDelivr.
 * Para uso offline, copia los pesos a public/ y define estas variables.
 */
export const FACE_MODEL_URL =
  import.meta.env.VITE_FACE_MODEL_URL ??
  "https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.15/model";

export const MEDIAPIPE_WASM_URL =
  import.meta.env.VITE_MEDIAPIPE_WASM_URL ??
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm";

export const FACE_LANDMARKER_MODEL_URL =
  import.meta.env.VITE_FACE_LANDMARKER_URL ??
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";

/** Umbral de distancia euclidiana para considerar dos rostros la misma persona. */
export const FACE_MATCH_THRESHOLD = Number(import.meta.env.VITE_FACE_MATCH_THRESHOLD ?? "0.5");
