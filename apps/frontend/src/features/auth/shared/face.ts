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

/** Devuelve el descriptor del rostro más prominente, o null si no hay uno claro. */
export async function extractDescriptor(
  video: HTMLVideoElement,
): Promise<DescriptorResult | null> {
  await loadFaceModels();
  const detection = await faceapi
    .detectSingleFace(video, new faceapi.SsdMobilenetv1Options({ minConfidence: 0.5 }))
    .withFaceLandmarks()
    .withFaceDescriptor();

  if (!detection) return null;
  return {
    descriptor: Array.from(detection.descriptor),
    score: detection.detection.score,
  };
}

/** Distancia euclidiana entre dos descriptores (menor = más parecidos). */
export function euclideanDistance(a: number[], b: number[]): number {
  let sum = 0;
  for (let i = 0; i < a.length; i++) sum += (a[i] - b[i]) ** 2;
  return Math.sqrt(sum);
}
