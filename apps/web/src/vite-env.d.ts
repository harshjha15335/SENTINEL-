/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "true" builds the read-only static demo for GitHub Pages (no API server). */
  readonly VITE_STATIC_DEMO?: string;
}
