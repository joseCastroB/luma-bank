/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_FACE_MODEL_URL?: string;
  readonly VITE_MEDIAPIPE_WASM_URL?: string;
  readonly VITE_FACE_LANDMARKER_URL?: string;
  readonly VITE_FACE_MATCH_THRESHOLD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
