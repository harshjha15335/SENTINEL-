/** Presentation preference only; never used for auth or authorization. */
const KEY = "sentinel:intro-complete:v1";

export function introWasCompleted(): boolean {
  try {
    return sessionStorage.getItem(KEY) === "true";
  } catch {
    return false;
  }
}

export function markIntroComplete(): void {
  try {
    sessionStorage.setItem(KEY, "true");
  } catch {
    // Browser storage is optional.
  }
}

export function resetIntro(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // Browser storage is optional.
  }
}
