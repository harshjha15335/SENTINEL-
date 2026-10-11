/** True in the GitHub Pages build: the app reads a bundled snapshot instead of calling the API. */
export const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === "true";

export const STATIC_DEMO_REFUSAL =
  "This is a read-only static snapshot on GitHub Pages. Nothing can be changed here and nothing is sent to PayPal. Run the full app to try this.";
