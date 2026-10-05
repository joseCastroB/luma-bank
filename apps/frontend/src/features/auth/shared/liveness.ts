/**
 * Prueba de vida con MediaPipe FaceLandmarker, guiada por el plan del servidor.
 *
 * El backend sortea una secuencia distinta en cada intento
 * (apps/backend/apps/accounts/services/liveness.py) y solo acepta la respuesta
 * si el cliente declara los MISMOS gestos en ese orden. Por eso aqui no hay un
 * reto fijo de "parpadeo + giro": hay que cumplir lo que pidio el servidor.
 *
 * Cada gesto se mide por separado y se registra solo cuando se mantiene el
 * tiempo suficiente, para que un parpadeo de un solo cuadro no cuente.
 */
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import { FACE_LANDMARKER_MODEL_URL, MEDIAPIPE_WASM_URL } from "@/lib/config";
import type { LivenessAction } from "@/lib/api";

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

export const LACTION_LABELS: Record<LivenessAction, string> = {
  blink: "Parpadea",
  head_turn_left: "Gira la cabeza a la izquierda",
  head_turn_right: "Gira la cabeza a la derecha",
};

/** Etiqueta por gesto, en el orden en que lo pide el servidor. */
export function describePlan(plan: LivenessAction[]): string {
  return plan.map((a) => LACTION_LABELS[a]).join(" y ");
}

export interface LivenessState {
  /** Gestos ya completados, en el orden en que sedine. */
  completed: LivenessAction[];
  /** Índice del gesto que se está pidiendo ahora (-1 si ya terminó). */
  currentIndex: number;
  faceVisible: boolean;
  hint: string;
  finished: boolean;
}

const BLINK_CLOSED = 0.5;
const BLINK_OPEN = 0.2;
const TURN_RATIO = 0.62;
/** Cuadros consecutivos que el gesto debe sostenerse para contar como hecho. */
const HOLD_FRAMES = 3;

/**
 * Crea un detector para un plan concreto.
 *
 * Se instancia uno por reto: el estado (`completed`) pertenece a una secuencia
 * concreta y no se puede reusar entre intentos, porque cada reto del servidor
 * es de un solo uso.
 */
export function createLivenessDetector(plan: LivenessAction[]) {
  const completed: LivenessAction[] = [];
  let eyesWereClosed = false;
  let holdFrames = 0;

  async function process(video: HTMLVideoElement, timestampMs: number): Promise<LivenessState> {
    const currentIndex = completed.length;
    const current = plan[currentIndex];

    const base: LivenessState = {
      completed: [...completed],
      currentIndex,
      faceVisible: false,
      hint: current ? LACTION_LABELS[current] : "Listo",
      finished: current === undefined,
    };
    if (!current) return base;

    const landmarker = await getLandmarker();
    const result = landmarker.detectForVideo(video, timestampMs);

    const face = result.faceLandmarks?.[0];
    const blend = result.faceBlendshapes?.[0]?.categories ?? [];
    if (!face || face.length === 0) {
      // Sin rostro no se avanza, pero tampoco se rompe la secuencia: el usuario
      // puede alejar la mano y volver a la posicion sin perder el reto.
      holdFrames = 0;
      return { ...base, hint: "Acerca tu rostro a la cámara." };
    }

    const held = detectHeld(current, face, blend);
    if (held) {
      if (holdFrames >= HOLD_FRAMES) {
        completed.push(current);
        holdFrames = 0;
        eyesWereClosed = false;
        const next = plan[completed.length];
        return {
          completed: [...completed],
          currentIndex: completed.length,
          faceVisible: true,
          hint: next ? `Ahora: ${LACTION_LABELS[next]}` : "¡Prueba de vida superada!",
          finished: completed.length === plan.length,
        };
      }
      holdFrames += 1;
    } else {
      holdFrames = 0;
    }

    return { ...base, faceVisible: true };
  }

  /**
   * ¿El gesto actual se sostiene en este cuadro?
   *
   * Para el parpadeo no basta con que el ojo esté cerrado: tiene que CLABSE y
   * volver a ABRIRSE, porque si solo se midiera "cerrado" el detector contaría
   * el parpadeo al primer cuadro en que el ojo ya se cerró.
   */
  function detectHeld(
    action: LivenessAction,
    face: readonly { x: number; y: number }[],
    blend: { categoryName?: string; displayName?: string; score: number }[],
  ): boolean {
    if (action === "blink") {
      const blinkScore = Math.max(score(blend, "eyeBlinkLeft"), score(blend, "eyeBlinkRight"));
      if (blinkScore > BLINK_CLOSED) eyesWereClosed = true;
      // Recieno cuando vuelve a abrirse tras haberse cerrado.
      return eyesWereClosed && blinkScore < BLINK_OPEN;
    }

    const nose = face[1];
    const right = face[234];
    const left = face[454];
    if (!nose || !right || !left) return false;
    const dRight = Math.hypot(nose.x - right.x, nose.y - right.y);
    const dLeft = Math.hypot(nose.x - left.x, nose.y - left.y);
    const ratio = Math.min(dRight, dLeft) / Math.max(dRight, dLeft);
    if (ratio >= TURN_RATIO) return false;
    // El ratio solo dice "estoy girado"; el lado lo decide cual distancia es
    // menor, porque el video se muestra espejado con -scale-x-100.
    const turningLeft = dLeft < dRight;
    return action === "head_turn_left" ? turningLeft : !turningLeft;
  }

  function reset() {
    completed.length = 0;
    eyesWereClosed = false;
    holdFrames = 0;
  }

  return { process, reset, isFinished: () => completed.length === plan.length };
}

function score(
  categories: { categoryName?: string; displayName?: string; score: number }[],
  name: string,
): number {
  const hit = categories.find((c) => (c.categoryName ?? c.displayName) === name);
  return hit?.score ?? 0;
}