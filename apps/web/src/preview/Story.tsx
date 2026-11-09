import { useGSAP } from "@gsap/react";
import { ArrowDown, ArrowRight, ArrowUpRight } from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useRef, useSyncExternalStore } from "react";
import { Link } from "react-router-dom";
import { DemoDossier } from "./Dossier";
import { Machine } from "./Machine";
import { EvidenceTape } from "./Tape";
import { storyStages } from "./fixtures";
import {
  evidenceGeometry,
  mix,
  placement,
  segment,
  smooth,
  stageBoundaries,
  transport,
} from "./scene";
import "./story.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);
const query = "(min-width: 901px) and (prefers-reduced-motion: no-preference)";
function subscribe(onChange: () => void) {
  const m = matchMedia(query);
  m.addEventListener("change", onChange);
  return () => m.removeEventListener("change", onChange);
}
const snapshot = () => matchMedia(query).matches;
export function EvidenceStory() {
  const desktop = useSyncExternalStore(subscribe, snapshot, () => false);
  return desktop ? <DesktopStory /> : <CompactStory />;
}
function updateTransport(root: HTMLElement, p: number) {
  const t = transport(p);
  root
    .querySelector('[data-reel="left"]')
    ?.setAttribute("transform", `rotate(${t.supplyAngle.toFixed(5)})`);
  root
    .querySelector('[data-reel="right"]')
    ?.setAttribute("transform", `rotate(${t.takeupAngle.toFixed(5)})`);
  root
    .querySelector('[data-wound="left"]')
    ?.setAttribute("r", String(t.supply));
  root
    .querySelector('[data-wound="right"]')
    ?.setAttribute("r", String(t.takeup));
  const internal = `M266 ${222 + t.supply} L266 347 340 369 459 363 564 331 564 ${207 + t.takeup}`;
  root
    .querySelectorAll("[data-internal-tape]")
    .forEach((el) => el.setAttribute("d", internal));
  root
    .querySelector("[data-tape]")
    ?.setAttribute("stroke-dashoffset", String(-t.distance));
  const diag = root.querySelector<SVGElement>("[data-diagnostic]");
  if (diag) diag.style.opacity = String(0.15 + t.advance * 0.85);
  const scan = root.querySelector<SVGElement>("[data-scan]");
  if (scan) scan.style.opacity = p >= 0.3 && p < 0.84 ? ".9" : "0";
  return t;
}
function DesktopStory() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const scene = root.current;
      if (!scene) return;
      const placementNode = scene.querySelector("[data-machine-placement]");
      const machine = scene.querySelector<SVGElement>("[data-machine-art]");
      const paths = scene.querySelectorAll<SVGPathElement>("[data-strip-path]");
      const marks = scene.querySelector<SVGPathElement>("[data-strip-marks]");
      const nodes = scene.querySelectorAll<SVGElement>("[data-path-node]");
      const risk = scene.querySelector<SVGElement>("[data-risk-visual]");
      const ring = scene.querySelector<SVGElement>("[data-risk-ring]");
      const frame = scene.querySelector<HTMLElement>("[data-dossier-frame]");
      const copy = scene.querySelector<HTMLElement>(".v2-scene-copy");
      const footer = scene.querySelector<HTMLElement>(".v2-scene-footer");
      const enter = scene.querySelector<HTMLElement>(".v2-scene-enter");
      const stages = scene.querySelectorAll<HTMLElement>("[data-story-stage]");
      const chips = scene.querySelectorAll("[data-chapter]");
      const status = scene.querySelector("[data-machine-status]");
      const pin = scene.querySelector<HTMLElement>(".v2-spatial-pin");
      let width = pin?.clientWidth ?? window.innerWidth,
        height = pin?.clientHeight ?? window.innerHeight;
      const render = (p: number) => {
        const t = updateTransport(scene, p),
          m = placement(p);
        placementNode?.setAttribute(
          "transform",
          `translate(${m.x} ${m.y}) scale(${m.scale}) rotate(${m.angle} 410 280)`,
        );
        if (machine)
          machine.style.opacity = String(1 - smooth(segment(p, 0.77, 0.91)));
        const geometry = evidenceGeometry(p, m.exitX, m.exitY);
        paths.forEach((path) => path.setAttribute("d", geometry.path));
        const total = geometry.length;
        const visible = smooth(segment(p, 0.2, 0.55));
        paths.forEach((path) => {
          path.style.strokeDasharray =
            path === marks ? "2 17" : `${visible * total} ${total + 1}`;
          path.style.strokeDashoffset =
            path === marks ? String(-t.distance) : "0";
          path.style.opacity = String(path === marks ? visible : 0.95);
        });
        // The data markings move within the growing physical strip, not independently of it.
        if (marks) {
          marks.style.clipPath = `inset(0 0 0 0)`;
          marks.style.opacity = String(visible * 0.7);
        }
        nodes.forEach((node, i) => {
          const at = Number(node.dataset.at ?? 0);
          const point = geometry.frameAt(at);
          node.setAttribute(
            "transform",
            `translate(${point.x} ${point.y}) rotate(${point.angle})`,
          );
          const appear = smooth(segment(visible, at - 0.04, at + 0.06));
          node.style.opacity = String(
            appear * (1 - smooth(segment(p, 0.67 + i * 0.02, 0.77 + i * 0.02))),
          );
        });
        if (risk) {
          const a = smooth(segment(p, 0.53, 0.64));
          risk.style.opacity = String(a * (1 - smooth(segment(p, 0.76, 0.91))));
          risk.setAttribute(
            "transform",
            `translate(1120 610) scale(${mix(0.72, 1, a)})`,
          );
        }
        ring?.setAttribute(
          "stroke-dashoffset",
          String(628.319 * (1 - 0.87 * smooth(segment(p, 0.53, 0.65)))),
        );
        const assembly = smooth(segment(p, 0.65, 0.99));
        if (frame) {
          const dx = width * 0.18 * (1 - assembly),
            dy = height * 0.13 * (1 - assembly);
          frame.style.transform = `translate(${dx}px,${dy}px) scale(${mix(0.38, 1, assembly)})`;
          frame.style.opacity = String(smooth(segment(p, 0.66, 0.76)));
          frame.style.borderRadius = `${18 * (1 - assembly)}px`;
          frame.style.visibility = p > 0.65 ? "visible" : "hidden";
        }
        const fade = 1 - smooth(segment(p, 0.64, 0.76));
        if (copy) {
          copy.style.opacity = String(fade);
          copy.inert = p > 0.8;
          copy.style.visibility = fade > 0 ? "visible" : "hidden";
        }
        const index = stageBoundaries.reduce<number>(
          (last, b, i) => (p >= b ? i : last),
          0,
        );
        const next = stageBoundaries[index + 1];
        const blend = next === undefined ? 0 : segment(p, next - 0.025, next);
        stages.forEach((el, i) => {
          const alpha = i === index ? 1 - blend : i === index + 1 ? blend : 0;
          el.style.opacity = String(alpha);
          el.style.visibility = alpha > 0 ? "visible" : "hidden";
          el.inert = i !== index;
        });
        chips.forEach((el, i) =>
          el.setAttribute("aria-current", i === index ? "step" : "false"),
        );
        if (footer) {
          footer.style.opacity = String(1 - segment(p, 0.85, 0.94));
          footer.inert = p > 0.94;
        }
        if (enter) {
          const show = p >= 0.96;
          enter.style.opacity = show ? "1" : "0";
          enter.style.visibility = show ? "visible" : "hidden";
          enter.inert = !show;
          if (show && footer?.contains(document.activeElement)) {
            enter
              .querySelector<HTMLAnchorElement>("a")
              ?.focus({ preventScroll: true });
          }
        }
        if (status)
          status.textContent =
            [
              "AWAITING INPUT",
              "READING INPUT",
              "EVIDENCE OUTPUT",
              "RISK / DEMO",
              "CASE CONTEXT",
              "WORKSPACE READY",
            ][index] ?? "";
        scene.dataset.progress = p.toFixed(4);
        scene.dataset.stage = String(index);
        scene.dataset.tapeDistance = t.distance.toFixed(3);
        const bar = scene.querySelector<HTMLElement>("[data-progress]");
        if (bar) bar.style.transform = `scaleX(${p})`;
        // At the end the physical strip dissolves into the actual, shared HTML workspace.
        const strip = scene.querySelector<SVGElement>("[data-evidence-strip]");
        if (strip)
          strip.style.opacity = String(1 - smooth(segment(p, 0.82, 0.95)));
      };
      const trigger = ScrollTrigger.create({
        id: "sentinel-evidence-reel",
        trigger: scene.querySelector(".v2-story-track"),
        start: "top top",
        end: "+=400%",
        pin: scene.querySelector(".v2-story-pin"),
        scrub: true,
        invalidateOnRefresh: true,
        onUpdate: (self) => render(self.progress),
        onRefresh: (self) => {
          width = pin?.clientWidth ?? window.innerWidth;
          height = pin?.clientHeight ?? window.innerHeight;
          render(self.progress);
        },
      });
      let active = true;
      void document.fonts.ready.then(() => {
        if (active) {
          ScrollTrigger.refresh();
          render(trigger.progress);
        }
      });
      render(trigger.progress);
      return () => {
        active = false;
      };
    },
    { scope: root },
  );
  const skip = () => {
    const end = document.getElementById("v2-after-story");
    end?.scrollIntoView({ behavior: "instant" });
    end?.focus({ preventScroll: true });
  };
  const chapter = (i: number) => {
    const t = ScrollTrigger.getById("sentinel-evidence-reel");
    if (t)
      window.scrollTo({
        top:
          t.start +
          (t.end - t.start) * (i === 5 ? 1 : (stageBoundaries[i] ?? 0)) +
          (i === 5 ? -1 : 1),
        behavior: "instant",
      });
  };
  return (
    <div
      ref={root}
      className="v2-story v2-spatial-story"
      data-progress="0"
      data-stage="0"
    >
      <StoryNav onSkip={skip} />
      <main>
        <div className="v2-story-track">
          <section
            className="v2-story-pin v2-spatial-pin"
            aria-label="Evidence Reel story"
          >
            <div className="v2-scene-meta">
              <span>
                <i className="v2-dot" /> EVIDENCE TRANSPORT / HUMAN DECISIONS
              </span>
              <span>SIMULATED / NO LIVE INFERENCE</span>
            </div>
            <svg
              className="v2-spatial-art"
              viewBox="0 0 1440 900"
              aria-hidden="true"
            >
              <EvidenceTape />
              <g data-machine-art>
                <g data-machine-placement>
                  <Machine />
                </g>
              </g>
            </svg>
            <div className="v2-scene-copy">
              {storyStages.map((s, i) => (
                <section
                  data-story-stage
                  className="v2-scene-stage"
                  key={s.step}
                >
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
                      <Link
                        className="v2-button"
                        to="/__v2-preview/dossier"
                        state={{ fromReel: true }}
                      >
                        Explore the system <ArrowUpRight size={17} />
                      </Link>
                      <Link className="v2-text-link" to="/">
                        Open Command Center <ArrowRight size={14} />
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
            <div className="v2-scene-enter" inert>
              <span>THE EVIDENCE IS NOW YOUR WORKSPACE.</span>
              <Link
                className="v2-button"
                to="/__v2-preview/dossier"
                state={{ fromReel: true }}
              >
                Enter the demo workspace <ArrowUpRight size={17} />
              </Link>
            </div>
            <footer className="v2-scene-footer">
              <span>
                <ArrowDown size={15} /> SCROLL TO UNFOLD THE EVIDENCE
              </span>
              <nav aria-label="Story chapters">
                {storyStages.map((s, i) => (
                  <button
                    key={s.step}
                    data-chapter
                    aria-label={`Go to ${s.label}`}
                    onClick={() => chapter(i)}
                  >
                    <span>{s.step}</span>
                    <i />
                  </button>
                ))}
              </nav>
              <span>ONE TRANSACTION. ONE CONTINUOUS THREAD.</span>
            </footer>
            <div className="v2-scene-progress" aria-hidden="true">
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
      const scene = root.current;
      if (!scene) return;
      const mm = gsap.matchMedia();
      mm.add("(prefers-reduced-motion: no-preference)", () => {
        const trigger = ScrollTrigger.create({
          id: "sentinel-mobile-evidence",
          trigger: scene.querySelector(".v2-compact-hero"),
          start: "top top",
          end: "bottom top",
          onUpdate: (self) => {
            updateTransport(scene, 0.14 + self.progress * 0.7);
            scene.dataset.progress = self.progress.toFixed(4);
          },
        });
        return () => trigger.kill();
      });
      return () => mm.revert();
    },
    { scope: root },
  );
  return (
    <div ref={root} className="v2-story v2-spatial-story v2-compact-story">
      <StoryNav
        onSkip={() => {
          const target = document.getElementById("v2-after-story");
          target?.scrollIntoView();
          target?.focus({ preventScroll: true });
        }}
      />
      <main>
        <section className="v2-compact-hero" data-story-stage>
          <p className="v2-eyebrow">THE ANATOMY OF FRAUD / SIMULATED</p>
          <h1>
            Fraud leaves a pattern.
            <br />
            <span>SENTINEL reads it.</span>
          </h1>
          <p>
            Follow one payment from its first signal to a focused investigation
            workspace.
          </p>
          <Link
            className="v2-button"
            to="/__v2-preview/dossier"
            state={{ fromReel: true }}
          >
            Explore the workspace <ArrowUpRight size={18} />
          </Link>
          <div className="v2-compact-machine">
            <Machine />
          </div>
          <div className="v2-mobile-output" aria-hidden="true">
            <svg viewBox="0 0 360 100" preserveAspectRatio="none">
              <path
                d="M335 0C380 75 260 25 260 55C260 110 0 50 0 100"
                fill="none"
                stroke="#7d9273"
                strokeWidth="13"
              />
              <path
                d="M335 0C380 75 260 25 260 55C260 110 0 50 0 100"
                fill="none"
                stroke="#172220"
                strokeWidth="8"
              />
              <path
                d="M335 0C380 75 260 25 260 55C260 110 0 50 0 100"
                fill="none"
                stroke="#c6ff4d"
                strokeWidth="2"
                strokeDasharray="2 10"
              />
            </svg>
          </div>
        </section>
        <div className="v2-compact-evidence">
          {storyStages.slice(1).map((s, j) => {
            const i = j + 1;
            return (
              <section data-story-stage id={`v2-stage-${i}`} key={s.step}>
                <p className="v2-eyebrow">
                  {s.step} / {s.label}
                </p>
                <h2>
                  {s.title} <span>{s.subtitle}</span>
                </h2>
                <p>{s.text}</p>
                {i === 1 && (
                  <strong>
                    $1,849.00 <small>USD · SIMULATED</small>
                  </strong>
                )}
                {i === 2 && (
                  <dl>
                    <div>
                      <dt>Payments · previous 24 hours</dt>
                      <dd>7</dd>
                    </div>
                    <div>
                      <dt>Amount vs merchant median</dt>
                      <dd>8.4×</dd>
                    </div>
                  </dl>
                )}
                {i === 3 && (
                  <strong className="v2-compact-score">
                    87 / 100 <small>ILLUSTRATIVE · HIGH RISK</small>
                  </strong>
                )}
              </section>
            );
          })}
        </div>
        <div
          className="v2-compact-workspace"
          inert
          aria-hidden="true"
          aria-label="Shared dossier opening"
        >
          <DemoDossier embedded />
        </div>
        <div className="v2-compact-open">
          <Link
            className="v2-button"
            to="/__v2-preview/dossier"
            state={{ fromReel: true }}
          >
            Enter the demo workspace <ArrowUpRight size={17} />
          </Link>
        </div>
        <StoryAfter />
      </main>
      <StoryFooter />
    </div>
  );
}
function StoryNav({ onSkip }: { onSkip: () => void }) {
  return (
    <header className="v2-spatial-nav">
      <Link className="v2-wordmark" to="/__v2-preview">
        <span className="v2-brand-icon">S</span>SENTINEL
        <span className="v2-nav-edition">/ INTELLIGENCE, IN CONTEXT.</span>
      </Link>
      <nav aria-label="Preview navigation">
        <button onClick={onSkip}>Skip story</button>
        <Link to="/__v2-preview/dossier" state={{ fromReel: true }}>
          Explore the workspace <ArrowUpRight size={15} />
        </Link>
      </nav>
    </header>
  );
}
function StoryAfter() {
  return (
    <section className="v2-after-story" id="v2-after-story" tabIndex={-1}>
      <div>
        <p className="v2-eyebrow">BEYOND THE NUMBER</p>
        <h2>
          See the payment.
          <br />
          <span>Understand the pattern.</span>
        </h2>
      </div>
      <div>
        <p>
          The physical thread becomes transaction context, readable risk
          factors, and a focused workspace. All example scores are illustrative.
        </p>
        <Link
          className="v2-button"
          to="/__v2-preview/dossier"
          state={{ fromReel: true }}
        >
          Open the Payment Dossier <ArrowUpRight size={18} />
        </Link>
        <Link className="v2-text-link" to="/__v2-preview/workspace">
          Inspect authorized records <ArrowRight size={15} />
        </Link>
      </div>
    </section>
  );
}
function StoryFooter() {
  return (
    <footer className="v2-final-footer">
      <span>SENTINEL / FORENSIC EDITORIAL</span>
      <span>LOCAL DESIGN PROTOTYPE · APPROVAL PENDING</span>
    </footer>
  );
}
