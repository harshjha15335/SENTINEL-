/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "true" builds the read-only static demo for GitHub Pages (no API server). */
  readonly VITE_STATIC_DEMO?: string;
  /** "hash" keeps routes in the URL hash, for hosts that cannot serve deep links. */
  readonly VITE_ROUTER?: string;
}
