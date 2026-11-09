import { ease, phase, mix } from "./money-scene";
/** Visual-only bridge. Native text reflows; the actual workspace is never scaled. */
export function ReceiptMorph() {
  return (
    <div
      className="v2-receipt-morph"
      data-receipt-morph
      aria-hidden="true"
      inert
    >
      <div data-morph-paper />
      <span data-morph-label>PAYMENT RECORD / DEMO-0148</span>
      <strong data-morph-amount>$1,849.00</strong>
      <span data-morph-currency>USD</span>
      <span data-morph-product>Studio equipment · DEMO-PAYER-148</span>
      <span data-morph-origin>SIMULATED · ILLUSTRATIVE DEMO</span>
      <i data-morph-rule />
    </div>
  );
}
function need<T extends Element>(parent: ParentNode, selector: string): T {
  const node = parent.querySelector<T>(selector);
  if (!node) throw new Error(`Missing receipt transition element: ${selector}`);
  return node;
}
export function receiptMorph(root: HTMLElement, frame: HTMLElement) {
  const overlay = need<HTMLElement>(root, "[data-receipt-morph]");
  const paper = need<HTMLElement>(overlay, "[data-morph-paper]");
  const amount = need<HTMLElement>(overlay, "[data-morph-amount]");
  const label = need<HTMLElement>(overlay, "[data-morph-label]");
  const currency = need<HTMLElement>(overlay, "[data-morph-currency]");
  const product = need<HTMLElement>(overlay, "[data-morph-product]");
  const origin = need<HTMLElement>(overlay, "[data-morph-origin]");
  const rule = need<HTMLElement>(overlay, "[data-morph-rule]");
  const header = need<HTMLElement>(frame, ".v2-dossier-header");
  const targetAmount = need<HTMLElement>(header, "[data-shared-amount]");
  const targetCurrency = need<HTMLElement>(targetAmount, "span");
  const targetLabel = need<HTMLElement>(header, ".v2-eyebrow");
  let bounds = { x: 0, y: 0, width: 1, height: 1 },
    a = { x: 0, y: 0, font: 60, spacing: 0 },
    l = { x: 0, y: 0, font: 11 },
    c = { x: 0, y: 0, font: 15 },
    prod = { x: 0, y: 0 };
  const refresh = () => {
    const f = frame.getBoundingClientRect(),
      h = header.getBoundingClientRect(),
      ar = targetAmount.getBoundingClientRect(),
      lr = targetLabel.getBoundingClientRect(),
      cr = targetCurrency.getBoundingClientRect(),
      pr = need<HTMLElement>(header, "p:last-child").getBoundingClientRect();
    bounds = { x: h.x - f.x, y: h.y - f.y, width: h.width, height: h.height };
    a = {
      x: ar.x - f.x,
      y: ar.y - f.y,
      font: parseFloat(getComputedStyle(targetAmount).fontSize),
      spacing: parseFloat(getComputedStyle(targetAmount).letterSpacing) || 0,
    };
    l = {
      x: lr.x - f.x,
      y: lr.y - f.y,
      font: parseFloat(getComputedStyle(targetLabel).fontSize),
    };
    c = {
      x: cr.x - f.x,
      y: cr.y - f.y,
      font: parseFloat(getComputedStyle(targetCurrency).fontSize),
    };
    prod = { x: pr.x - f.x, y: pr.y - f.y };
  };
  refresh();
  const put = (el: HTMLElement, x: number, y: number, font?: number) => {
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    if (font) el.style.fontSize = `${font}px`;
  };
  return {
    refresh,
    render(p: number, width: number, height: number) {
      const grow = ease(phase(p, 0.76, 0.89)),
        unfold = ease(phase(p, 0.88, 0.99)),
        handoff = ease(phase(p, 0.89, 0.93));
      const scale = Math.min(width / 1440, height / 900),
        ox = (width - 1440 * scale) / 2,
        oy = (height - 900 * scale) / 2;
      const x = mix(ox + 904 * scale, bounds.x, grow),
        y = mix(oy + 274 * scale, bounds.y - 18, grow),
        w = mix(262 * scale, bounds.width, grow),
        h = mix(322 * scale, bounds.height + 18, grow);
      overlay.style.visibility = p >= 0.76 && p < 0.93 ? "visible" : "hidden";
      overlay.style.opacity = String(1 - handoff);
      put(paper, x, y);
      paper.style.width = `${w}px`;
      paper.style.height = `${h}px`;
      paper.style.borderRadius = `${mix(3, 0, grow)}px`;
      paper.style.backgroundColor = `rgb(${mix(255, 247, grow)} ${mix(255, 244, grow)} ${mix(255, 238, grow)})`;
      put(
        amount,
        mix(ox + 929 * scale, a.x, grow),
        mix(oy + 367 * scale, a.y, grow),
        mix(35 * scale, a.font, grow),
      );
      amount.style.letterSpacing = `${mix(0, a.spacing, grow)}px`;
      put(
        label,
        mix(ox + 929 * scale, l.x, grow),
        mix(oy + 335 * scale, l.y, grow),
        mix(11 * scale, l.font, grow),
      );
      put(
        currency,
        mix(ox + 929 * scale, a.x, grow),
        mix(oy + 367 * scale, a.y, grow) +
          mix(35 * scale, a.font, grow) * 1.15 +
          8,
        mix(11 * scale, c.font, grow),
      );
      currency.style.opacity = String(1 - ease(phase(grow, 0.8, 1)));
      put(
        product,
        mix(ox + 929 * scale, prod.x, grow),
        mix(oy + 520 * scale, prod.y, grow),
        13,
      );
      product.style.opacity = String(ease(phase(grow, 0.8, 1)));
      put(origin, x + 25, y + h - 48, 11);
      origin.style.opacity = String(1 - grow);
      put(rule, x, y + h);
      rule.style.width = `${w}px`;
      rule.style.opacity = String(grow);
      // Reveal full-size native layout outward from its own payment header.
      const left = mix(bounds.x, 0, unfold),
        top = mix(bounds.y, 0, unfold),
        right = mix(width - bounds.x - bounds.width, 0, unfold),
        bottom = mix(Math.max(0, height - bounds.y - bounds.height), 0, unfold);
      frame.style.transform = "none";
      frame.style.clipPath = `inset(${top}px ${right}px ${bottom}px ${left}px)`;
      frame.style.opacity = p >= 0.88 ? "1" : "0";
      frame.style.visibility = p >= 0.88 ? "visible" : "hidden";
      header.style.opacity = String(handoff);
      root.dataset.morphProgress = grow.toFixed(4);
    },
  };
}
