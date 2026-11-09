import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowUpRight, ArrowDown } from "lucide-react";
import { useRef, useSyncExternalStore } from "react";
import { Link } from "react-router-dom";
import { ReceiptMorph, receiptMorph } from "./ReceiptMorph";
import { DemoDossier } from "./Dossier";
import { storyStages } from "./fixtures";
import { chapters, ease, phase, mix, moneyScene } from "./money-scene";
import { Wallet, Banknote, Receipt } from "./Wallet";
import "./story.css";
gsap.registerPlugin(ScrollTrigger, useGSAP);
const query = "(min-width: 901px) and (prefers-reduced-motion: no-preference)";
function subscribe(fn: () => void) {
  const m = matchMedia(query);
  m.addEventListener("change", fn);
  return () => m.removeEventListener("change", fn);
}
export function MoneyStory() {
  const desktop = useSyncExternalStore(
    subscribe,
    () => matchMedia(query).matches,
    () => false,
  );
  return desktop ? <DesktopStory /> : <CompactStory />;
}
function skip() {
  const el = document.getElementById("v2-after-story");
  el?.scrollIntoView({ behavior: "instant" });
  el?.focus({ preventScroll: true });
}
function StoryNav() {
  return (
    <header className="v2-story-nav">
      <Link className="v2-wordmark" to="/">
        <span className="v2-brand-icon">S</span>SENTINEL
        <span className="v2-nav-edition">FOLLOW THE MONEY</span>
      </Link>
      <nav aria-label="Preview navigation">
        <button onClick={skip}>Skip story</button>
        <Link to="/demo-payment" className="v2-nav-cta">
          Explore simulated demo <ArrowUpRight size={16} />
        </Link>
      </nav>
    </header>
  );
}
function DesktopStory() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const el = root.current;
      if (!el) return;
      const wallet = el.querySelector<SVGElement>("[data-wallet-placement]"),
        fold = el.querySelector<SVGElement>("[data-wallet-fold]"),
        receipt = el.querySelector<SVGElement>("[data-hero-receipt]"),
        notes = el.querySelectorAll<SVGElement>("[data-note]"),
        secondary = el.querySelector<SVGElement>("[data-secondary-receipt]"),
        field = el.querySelector<SVGElement>("[data-field]"),
        signals = el.querySelectorAll<SVGElement>("[data-signal]"),
        trail = el.querySelector<SVGElement>("[data-money-path]"),
        accent = el.querySelector("[data-hero-receipt] [data-receipt-accent]"),
        copy = el.querySelector<HTMLElement>(".v2-scene-copy"),
        frame = el.querySelector<HTMLElement>("[data-dossier-frame]"),
        enter = el.querySelector<HTMLElement>(".v2-scene-enter"),
        footer = el.querySelector<HTMLElement>(".v2-scene-footer"),
        stages = el.querySelectorAll<HTMLElement>("[data-story-stage]"),
        buttons = el.querySelectorAll("[data-chapter]"),
        bar = el.querySelector<HTMLElement>("[data-progress]");
      const edition = el.querySelector<HTMLElement>(".v2-story-edition");
      const pin = el.querySelector<HTMLElement>(".v2-story-pin");
      let width = pin?.clientWidth ?? innerWidth,
        height = pin?.clientHeight ?? innerHeight;
      const morph = frame ? receiptMorph(el, frame) : null;
      const interior = el.querySelector<SVGElement>("[data-wallet-interior]");
      const render = (progress: number) => {
        const s = moneyScene(progress),
          p = s.p,
          w = s.wallet,
          r = s.receipt;
        if (edition)
          edition.style.opacity = String(1 - ease(phase(p, 0.1, 0.2)));
        if (wallet) {
          wallet.setAttribute(
            "transform",
            `translate(${w.x} ${w.y}) scale(${w.scale}) rotate(${w.angle} 300 210)`,
          );
          wallet.style.opacity = String(w.opacity);
        }
        if (interior) interior.style.opacity = String(s.open);
        if (fold)
          fold.style.transform = `translateY(${-68 * s.open}px) scaleY(${1 - 0.75 * s.open}) rotate(${-7 * s.open}deg)`;
        if (receipt) {
          receipt.setAttribute(
            "transform",
            `translate(${r.x} ${r.y}) rotate(${r.angle}) scale(${r.scale})`,
          );
          receipt.style.opacity = String(r.opacity);
        }
        const notePaths = [
          { x: 790, y: 220, s: 0.82, r: -27 },
          { x: 1280, y: 625, s: 0.72, r: 24 },
          { x: 1010, y: 160, s: 0.5, r: 12 },
          { x: 815, y: 660, s: 0.54, r: -18 },
          { x: 1235, y: 360, s: 0.46, r: 34 },
          { x: 1080, y: 715, s: 0.63, r: -12 },
        ];
        notes.forEach((n, i) => {
          const spec = notePaths[i] ?? { x: 1100, y: 400, s: 0.5, r: 0 },
            release = ease(phase(p, 0.12 + i * 0.014, 0.33 + i * 0.014)),
            travel = ease(phase(p, 0.35, 0.65));
          const x =
            mix(1040, spec.x, release) + (i % 2 === 0 ? -100 : 90) * travel;
          const y =
            mix(390, spec.y, release) -
            Math.sin(release * Math.PI) * 130 -
            travel * (i % 2 === 0 ? 140 : 80);
          n.setAttribute(
            "transform",
            `translate(${x} ${y}) rotate(${mix(-8, spec.r, release) + travel * 40}) skewX(${Math.sin(release * Math.PI) * mix(-10, 10, i / 5)}) scale(${mix(0.12, spec.s, release)},${mix(0.12, spec.s * (0.78 + 0.16 * Math.cos(release * Math.PI)), release)})`,
          );
          n.style.opacity = String(
            ease(phase(p, 0.13 + i * 0.014, 0.19 + i * 0.014)) *
              (1 - ease(phase(p, 0.47 + i * 0.01, 0.66 + i * 0.01))),
          );
        });
        if (secondary) {
          const a = ease(phase(p, 0.17, 0.39)),
            exit = ease(phase(p, 0.43, 0.62));
          secondary.setAttribute(
            "transform",
            `translate(${mix(1040, 1280, a) + 230 * exit} ${430 - 260 * Math.sin(a * Math.PI) + 150 * a - 70 * exit}) rotate(${mix(-8, 18, a) + 25 * exit}) scale(${mix(0.08, 0.62, a)})`,
          );
          secondary.style.opacity = String(
            ease(phase(p, 0.17, 0.23)) * (1 - exit),
          );
        }
        if (trail) {
          trail.style.opacity = String(
            ease(phase(p, 0.23, 0.34)) * (1 - ease(phase(p, 0.6, 0.75))),
          );
          trail.style.strokeDashoffset = String(
            1200 * (1 - ease(phase(p, 0.23, 0.6))),
          );
        }
        if (accent)
          accent.setAttribute("fill", p >= 0.44 ? "#FF865C" : "#7547EB");
        if (field) {
          field.style.opacity = String(s.field);
          field.setAttribute(
            "transform",
            `translate(1035 440) scale(${mix(1.12, 1, ease(phase(p, 0.53, 0.65)))})`,
          );
        }
        signals.forEach((n, i) => {
          n.style.opacity = String(
            ease(phase(p, 0.57 + i * 0.025, 0.65 + i * 0.025)) *
              (1 - ease(phase(p, 0.75, 0.82))),
          );
        });
        if (copy) {
          const fade = 1 - ease(phase(p, 0.73, 0.84));
          copy.style.opacity = String(fade);
          copy.style.visibility = fade > 0 ? "visible" : "hidden";
          copy.inert = p > 0.82;
        }
        stages.forEach((n, i) => {
          // Fade out before the boundary, then fade in the next chapter: never stack headlines.
          const next = chapters[s.stage + 1],
            start = chapters[s.stage] ?? 0;
          const out =
            next === undefined ? 1 : 1 - ease(phase(p, next - 0.02, next));
          const incoming =
            s.stage === 0 ? 1 : ease(phase(p, start, start + 0.015));
          const a = i === s.stage ? out * incoming : 0;
          n.style.opacity = String(a);
          n.style.visibility = a > 0 ? "visible" : "hidden";
          n.inert = i !== s.stage;
        });
        morph?.render(p, width, height);
        if (footer) {
          footer.style.opacity = String(1 - ease(phase(p, 0.77, 0.88)));
          footer.inert = p > 0.88;
        }
        if (enter) {
          const show = p >= 0.97;
          enter.style.visibility = show ? "visible" : "hidden";
          enter.inert = !show;
          if (show && footer?.contains(document.activeElement))
            enter
              .querySelector<HTMLAnchorElement>("a")
              ?.focus({ preventScroll: true });
        }
        buttons.forEach((n, i) =>
          n.setAttribute("aria-current", i === s.stage ? "step" : "false"),
        );
        if (bar) bar.style.transform = `scaleX(${p})`;
        el.dataset.progress = p.toFixed(4);
        el.dataset.stage = String(s.stage);
        el.dataset.walletOpen = s.open.toFixed(4);
      };
      const t = ScrollTrigger.create({
        id: "sentinel-money-trail",
        trigger: el.querySelector(".v2-story-track"),
        start: "top top",
        end: "+=400%",
        pin: el.querySelector(".v2-story-pin"),
        scrub: true,
        invalidateOnRefresh: true,
        onUpdate: (self) => render(self.progress),
        onRefresh: (self) => {
          width = pin?.clientWidth ?? innerWidth;
          height = pin?.clientHeight ?? innerHeight;
          morph?.refresh();
          render(self.progress);
        },
      });
      let active = true;
      void document.fonts.ready.then(() => {
        if (active) {
          ScrollTrigger.refresh();
          render(t.progress);
        }
      });
      render(t.progress);
      return () => {
        active = false;
      };
    },
    { scope: root },
  );
  const chapter = (i: number) => {
    const t = ScrollTrigger.getById("sentinel-money-trail");
    if (t)
      scrollTo({
        top:
          t.start +
          (t.end - t.start) * (i === 6 ? 0.999 : (chapters[i] ?? 0) + 0.02),
        behavior: "instant",
      });
  };
  return (
    <div
      ref={root}
      className="v2-story v2-money-story"
      data-stage="0"
      data-progress="0"
    >
      <StoryNav />
      <main>
        <div className="v2-story-track">
          <section className="v2-story-pin" aria-label="Follow the Money story">
            <div className="v2-story-edition">
              <span>FINANCIAL INTELLIGENCE, IN MOTION.</span>
              <span>SIMULATED STORY · ILLUSTRATIVE RISK</span>
            </div>
            <svg
              className="v2-money-art"
              viewBox="0 0 1440 900"
              aria-hidden="true"
            >
              <defs>
                <radialGradient id="money-aura">
                  <stop stopColor="#E9E0FF" />
                  <stop offset="1" stopColor="#F7F4EE" stopOpacity="0" />
                </radialGradient>
              </defs>
              <ellipse
                cx="1030"
                cy="450"
                rx="410"
                ry="355"
                fill="url(#money-aura)"
              />
              <path
                data-money-path
                d="M1060 490C750 630 710 170 1040 230S1440 520 1130 700"
                fill="none"
                stroke="#B6A0DE"
                strokeWidth="2"
                strokeDasharray="4 10"
              />
              {Array.from({ length: 6 }, (_, i) => (
                <g key={i} data-note>
                  <Banknote variant={i % 2} />
                </g>
              ))}
              <g data-secondary-receipt>
                <Receipt secondary />
              </g>
              <g data-field>
                <rect
                  x="-167"
                  y="-201"
                  width="334"
                  height="400"
                  rx="36"
                  fill="#E9E0FF"
                  fillOpacity=".4"
                  stroke="#7547EB"
                  strokeWidth="1.5"
                />
                <path
                  d="M-181-145V-191Q-181-215-157-215H-112M112-215H157Q181-215 181-191V-145M181 140V190Q181 214 157 214H112M-112 214H-157Q-181 214-181 190V140"
                  fill="none"
                  stroke="#7547EB"
                  strokeWidth="3"
                />
                <path
                  d="M-158-8H158"
                  stroke="#7547EB"
                  strokeOpacity=".3"
                  strokeWidth="2"
                />
              </g>
              <g data-hero-receipt>
                <Receipt />
              </g>
              <g data-wallet-placement>
                <Wallet />
              </g>
              <g data-signal transform="translate(765 650)">
                <path d="M0 0 80-45" stroke="#A78FCB" fill="none" />
                <rect
                  x="-70"
                  y="-5"
                  width="195"
                  height="69"
                  rx="14"
                  fill="white"
                  stroke="#DED7E5"
                />
                <text x="-50" y="20" fontSize="12" fill="#686273">
                  PAST 24 HOURS
                </text>
                <text x="-50" y="46" fontSize="22" fill="#201A2B">
                  7 payments
                </text>
              </g>
              <g data-signal transform="translate(1240 260)">
                <path d="M0 40-85 25" stroke="#A78FCB" />
                <rect
                  x="-80"
                  y="-30"
                  width="185"
                  height="68"
                  rx="14"
                  fill="white"
                  stroke="#DED7E5"
                />
                <text x="-62" y="-5" fontSize="12" fill="#686273">
                  AMOUNT DEVIATION
                </text>
                <text x="-62" y="22" fontSize="22" fill="#201A2B">
                  8.4× median
                </text>
              </g>
              <g data-signal transform="translate(1110 690)">
                <rect
                  x="-115"
                  y="-20"
                  width="250"
                  height="67"
                  rx="16"
                  fill="#FF865C"
                />
                <text
                  x="-95"
                  y="7"
                  fontSize="17"
                  fontWeight="600"
                  fill="#201A2B"
                >
                  87 / 100 · HIGH RISK
                </text>
                <text x="-95" y="29" fontSize="11" fill="#201A2B">
                  ILLUSTRATIVE · NOT LIVE INFERENCE
                </text>
              </g>
            </svg>
            <div className="v2-scene-copy">
              {storyStages.map((s, i) => (
                <section key={s.step} data-story-stage>
                  <p className="v2-eyebrow">
                    {s.step} / {s.label}
                  </p>
                  <h1>
                    {s.title}
                    <br />
                    <span>{s.subtitle}</span>
                  </h1>
                  <p>{s.text}</p>
                  {i === 0 && (
                    <>
                      <Link className="v2-button" to="/demo-payment">
                        Explore simulated demo <ArrowUpRight size={18} />
                      </Link>
                      <small>Explore an interactive, simulated payment.</small>
                      <Link className="v2-auth-link" to="/app/transactions">
                        Open authenticated workspace <ArrowUpRight size={15} />
                      </Link>
                    </>
                  )}
                </section>
              ))}
            </div>
            <div
              className="v2-destination-preview"
              data-dossier-frame
              inert
              aria-hidden="true"
            >
              <DemoDossier embedded />
            </div>
            <ReceiptMorph />
            <div className="v2-scene-enter" inert>
              <span>FROM PAYMENT TO PERSPECTIVE.</span>
              <Link className="v2-button" to="/demo-payment">
                Explore simulated demo <ArrowUpRight size={18} />
              </Link>
            </div>
            <footer className="v2-scene-footer">
              <span>
                <ArrowDown size={15} /> SCROLL TO FOLLOW THE MONEY
              </span>
              <nav aria-label="Story chapters">
                {storyStages.map((s, i) => (
                  <button
                    key={s.step}
                    data-chapter
                    aria-label={`Go to ${s.label}`}
                    onClick={() => chapter(i)}
                  >
                    {s.step}
                    <i />
                  </button>
                ))}
              </nav>
              <span>01 PAYMENT. A CLEARER PICTURE.</span>
            </footer>
            <div className="v2-scene-progress">
              <i data-progress />
            </div>
          </section>
        </div>
        <StoryAfter />
      </main>
      <StoryFooter />
    </div>
  );
}
function CompactStory() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const el = root.current;
      if (!el) return;
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const fold = el.querySelector<SVGElement>("[data-wallet-fold]");
        const interior = el.querySelector<SVGElement>("[data-wallet-interior]");
        const t = ScrollTrigger.create({
          id: "sentinel-mobile-money",
          trigger: el.querySelector(".v2-compact-hero"),
          start: "top top",
          end: "bottom top",
          onUpdate: (s) => {
            if (interior) interior.style.opacity = String(s.progress);
            if (fold)
              fold.style.transform = `translateY(${-68 * s.progress}px) scaleY(${1 - 0.75 * s.progress})`;
            el.dataset.progress = s.progress.toFixed(4);
          },
        });
        return () => t.kill();
      });
      return () => mm.revert();
    },
    { scope: root },
  );
  return (
    <div ref={root} className="v2-story v2-compact-story">
      <StoryNav />
      <main>
        <section className="v2-compact-hero" data-story-stage>
          <p className="v2-eyebrow">01 / THE WALLET</p>
          <h1>
            Every payment
            <br />
            <span>has a story.</span>
          </h1>
          <p>Not every story ends well.</p>
          <Link className="v2-button" to="/demo-payment">
            Explore simulated demo <ArrowUpRight size={18} />
          </Link>
          <Link className="v2-auth-link" to="/app/transactions">
            Open authenticated workspace <ArrowUpRight size={15} />
          </Link>
          <div className="v2-compact-wallet">
            <Wallet />
          </div>
          <p className="v2-fine">SIMULATED STORY · ILLUSTRATIVE RISK</p>
        </section>
        <div className="v2-compact-narrative">
          {storyStages.slice(1).map((s, i) => (
            <section key={s.step} data-story-stage>
              <p className="v2-eyebrow">
                {s.step} / {s.label}
              </p>
              <h2>
                {s.title} <span>{s.subtitle}</span>
              </h2>
              <p>{s.text}</p>
              {i === 1 && (
                <div className="v2-mobile-receipt">
                  <span>DEMO-0148 · SIMULATED</span>
                  <strong>$1,849.00</strong>
                  <span>1 Nov 2026 · 10:43 UTC</span>
                </div>
              )}
              {i === 3 && (
                <dl className="v2-mobile-signals">
                  <div>
                    <dt>Payments · past 24h</dt>
                    <dd>7</dd>
                  </div>
                  <div>
                    <dt>Amount / merchant median</dt>
                    <dd>8.4×</dd>
                  </div>
                  <div>
                    <dt>Illustrative risk</dt>
                    <dd>87 / 100</dd>
                  </div>
                </dl>
              )}
            </section>
          ))}
        </div>
        <div className="v2-compact-workspace" inert aria-hidden="true">
          <DemoDossier embedded />
        </div>
        <StoryAfter />
      </main>
      <StoryFooter />
    </div>
  );
}
function StoryAfter() {
  return (
    <section className="v2-after-story" id="v2-after-story" tabIndex={-1}>
      <div>
        <p className="v2-eyebrow">THE HUMAN MAKES THE CALL.</p>
        <h2>
          Money moves. Risk hides.
          <br />
          <span>SENTINEL reveals it.</span>
        </h2>
      </div>
      <div>
        <p>
          A clearer view of each payment. A thoughtful place to decide what
          happens next.
        </p>
        <Link className="v2-button" to="/demo-payment">
          Open the simulated dossier <ArrowUpRight size={18} />
        </Link>
        <Link className="v2-text-link" to="/app/transactions">
          Open authenticated workspace <ArrowUpRight size={15} />
        </Link>
      </div>
    </section>
  );
}
function StoryFooter() {
  return (
    <footer className="v2-final-footer">
      <span>SENTINEL — FOLLOW THE MONEY</span>
      <span>LOCAL DESIGN PROTOTYPE · APPROVAL PENDING</span>
    </footer>
  );
}
