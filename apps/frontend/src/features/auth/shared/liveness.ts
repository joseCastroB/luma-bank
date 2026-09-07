/**
 * Prueba de vida con MediaPipe FaceLandmarker.
 * Reto: el usuario debe (1) parpadear y (2) girar la cabeza a un lado.
 * Ambas señales juntas hacen muy difícil pasar la prueba con una foto.
 */
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import { FACE_LANDMARKER_MODEL_URL, MEDIAPIPE_WASM_URL } from "@/lib/config";

let landmarkerPromise: Promise<FaceLandmarker> | null = null;

function getLandmarker(): Promise<FaceLandmarker> {
  if (!landmarkerPromise) {
    landmarkerPromise = FilesetResolver.forVisionTasks(MEDIAPIPE_WASM_URL).then((fileset) =>
      FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: FACE_LANDMARKER_MODEL_URL, delegate: "GPU" },
        runningMode: "VIDEO",
        numFaces: 1,
        outputFaceBlendshapes: true,
      }),
    );
  }
  return landmarkerPromise;
}

export type LivenessCheck = "blink" | "head_turn";

export interface LivenessState {
  passed: boolean;
  checks: LivenessCheck[];
  hint: string;
  faceVisible: boolean;
  /** Rostro de frente ahora mismo (para capturar el descriptor en buen ángulo). */
  frontal: boolean;
  /** Ojos abiertos ahora mismo. */
  eyesOpen: boolean;
}

const BLINK_CLOSED = 0.5;
const BLINK_OPEN = 0.2;
const TURN_RATIO = 0.62;
const FRONTAL_RATIO = 0.86;
const EYES_OPEN_MAX = 0.28;

/** Máquina de estados de la prueba de vida; se alimenta cuadro a cuadro. */
export function createLivenessDetector() {
  let eyesWereClosed = false;
  let blinked = false;
  let turned = false;

  async function process(video: HTMLVideoElement, timestampMs: number): Promise<LivenessState> {
    const landmarker = await getLandmarker();
    const result = landmarker.detectForVideo(video, timestampMs);

    const face = result.faceLandmarks?.[0];
    const blend = result.faceBlendshapes?.[0]?.categories ?? [];
    if (!face || face.length === 0) {
      return {
        passed: false,
        checks: activeChecks(),
        hint: "Acerca tu rostro a la cámara.",
        faceVisible: false,
        frontal: false,
        eyesOpen: false,
      };
    }

    // --- parpadeo (blendshapes de ojos) ---
    const blinkScore = Math.max(score(blend, "eyeBlinkLeft"), score(blend, "eyeBlinkRight"));
    if (blinkScore > BLINK_CLOSED) eyesWereClosed = true;
    if (eyesWereClosed && blinkScore < BLINK_OPEN) {
      blinked = true;
      eyesWereClosed = false;
    }
    const eyesOpen = blinkScore < EYES_OPEN_MAX;

    // --- giro de cabeza (geometría de landmarks) ---
    let ratio = 1;
    const nose = face[1];
    const right = face[234];
    const left = face[454];
    if (nose && right && left) {
      const dR = Math.hypot(nose.x - right.x, nose.y - right.y);
      const dL = Math.hypot(nose.x - left.x, nose.y - left.y);
      ratio = Math.min(dR, dL) / Math.max(dR, dL);
      if (ratio < TURN_RATIO) turned = true;
    }
    const frontal = ratio > FRONTAL_RATIO;

    const passed = blinked && turned;
    return {
      passed,
      checks: activeChecks(),
      faceVisible: true,
      frontal,
      eyesOpen,
      hint: passed
        ? frontal && eyesOpen
          ? "¡Listo! Capturando…"
          : "Perfecto. Ahora mira al frente con los ojos abiertos."
        : !blinked
          ? "Parpadea una vez, mirando a la cámara."
          : "Ahora gira lentamente la cabeza a un lado.",
    };
  }

  function activeChecks(): LivenessCheck[] {
    const c: LivenessCheck[] = [];
    if (blinked) c.push("blink");
    if (turned) c.push("head_turn");
    return c;
  }

  function reset() {
    eyesWereClosed = false;
    blinked = false;
    turned = false;
  }

  return { process, reset };
}

function score(categories: { categoryName?: string; displayName?: string; score: number }[], name: string): number {
  const hit = categories.find((c) => (c.categoryName ?? c.displayName) === name);
  return hit?.score ?? 0;
}
