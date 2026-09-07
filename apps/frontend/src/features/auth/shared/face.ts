/**
 * Extracción del descriptor facial (embedding de 128 dimensiones) con
 * @vladmandic/face-api. Los pesos se cargan una sola vez desde FACE_MODEL_URL.
 * La imagen NUNCA sale del navegador: solo se envía el vector al backend.
 */
import * as faceapi from "@vladmandic/face-api";
import { FACE_MODEL_URL } from "@/lib/config";

export const DESCRIPTOR_ALGORITHM = "vladmandic/face-api@1.7.15 ssdMobilenetv1 128d";

let loadPromise: Promise<void> | null = null;

export function loadFaceModels(): Promise<void> {
  if (!loadPromise) {
    loadPromise = Promise.all([
      faceapi.nets.ssdMobilenetv1.loadFromUri(FACE_MODEL_URL),
      faceapi.nets.faceLandmark68Net.loadFromUri(FACE_MODEL_URL),
      faceapi.nets.faceRecognitionNet.loadFromUri(FACE_MODEL_URL),
    ]).then(() => undefined);
  }
  return loadPromise;
}

export interface DescriptorResult {
  descriptor: number[];
  /** confianza de la detección (0-1) */
  score: number;
}

/**
 * Toma varias muestras y devuelve el descriptor de la detección con mayor
 * confianza (reduce el ruido frente a un solo cuadro). null si no hay rostro claro.
 */
export async function extractDescriptor(
  video: HTMLVideoElement,
  samples = 4,
): Promise<DescriptorResult | null> {
  await loadFaceModels();
  const opts = new faceapi.SsdMobilenetv1Options({ minConfidence: 0.5 });

  let best: DescriptorResult | null = null;
  for (let i = 0; i < samples; i++) {
    const detection = await faceapi
      .detectSingleFace(video, opts)
      .withFaceLandmarks()
      .withFaceDescriptor();
    if (detection) {
      const score = detection.detection.score;
      if (!best || score > best.score) {
        best = { descriptor: Array.from(detection.descriptor), score };
      }
    }
    if (i < samples - 1) await new Promise((r) => setTimeout(r, 120));
  }
  return best;
}

/** Distancia euclidiana entre dos descriptores (menor = más parecidos). */
export function euclideanDistance(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += (a[i] - b[i]) ** 2;
  return Math.sqrt(sum);
}
