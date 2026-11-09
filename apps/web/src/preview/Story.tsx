import { useGSAP } from "@gsap/react";
import { ArrowDown, ArrowRight, ArrowUpRight, ChevronDown } from "lucide-react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useRef } from "react";
import { Link } from "react-router-dom";
import { Machine } from "./Machine";
import { storyStages } from "./fixtures";

gsap.registerPlugin(ScrollTrigger, useGSAP);
const boundaries = [0, 0.14, 0.3, 0.48, 0.66, 0.84];
export function EvidenceStory() {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    () => {
      const scene = root.current;
      if (!scene) return;
      const mm = gsap.matchMedia();
      mm.add(
        "(min-width: 901px) and (prefers-reduced-motion: no-preference)",
        () => {
          const stages = gsap.utils.toArray<HTMLElement>(
            "[data-story-stage]",
            scene,
          );
          const chips = gsap.utils.toArray<HTMLElement>(
            "[data-chapter]",
            scene,
          );
          const status = scene.querySelector("[data-machine-status]");
          const reels = scene.querySelectorAll("[data-reel]");
          const tape = scene.querySelector("[data-tape]");
          const diagnostic = scene.querySelector("[data-diagnostic]");
          const scanner = scene.querySelector("[data-scan]");
          const progress = scene.querySelector("[data-progress]");
          const caseReveal =
            scene.querySelector<HTMLElement>("[data-case-reveal]");
          const machine = scene.querySelector(".v2-machine-wrap");
          const readouts =
            scene.querySelectorAll<HTMLElement>("[data-readout]");
          // Initial values are captured by the GSAP context and reverted on breakpoint/unmount.
          gsap.set(reels, { rotation: 0, svgOrigin: "0 0" });
          gsap.set(tape, { strokeDashoffset: 0 });
          gsap.set(diagnostic, { opacity: 0.15 });
          gsap.set(scanner, { opacity: 0 });
          gsap.set(progress, { scaleX: 0, transformOrigin: "left" });
          gsap.set(caseReveal, { opacity: 0, y: 35 });
          gsap.set(machine, { scale: 1, y: 0 });
          const setRotation = gsap.quickSetter(reels, "rotation", "deg");
          const setTape = gsap.quickSetter(tape, "strokeDashoffset");
          const setDiagnostic = gsap.quickSetter(diagnostic, "opacity");
          const setProgress = gsap.quickSetter(progress, "scaleX");
          const setCaseOpacity = gsap.quickSetter(caseReveal, "opacity");
          const setCaseY = gsap.quickSetter(caseReveal, "y", "px");
          const setScaleX = gsap.quickSetter(machine, "scaleX");
          const setScaleY = gsap.quickSetter(machine, "scaleY");
          let previousIndex = -1;
          const render = (p: number) => {
            // Constant apparent spool radius; tape distance is shared by both reels.
            const travel = Math.max(0, Math.min(1, (p - 0.14) / 0.7)) * 2000;
            setRotation(((travel / 78) * 180) / Math.PI);
            setTape(-travel);
            setDiagnostic(0.15 + Math.min(1, travel / 80) * 0.85);
            const index = boundaries.reduce(
              (last, b, i) => (p >= b ? i : last),
              0,
            );
            const nextBoundary = boundaries[index + 1];
            const blend =
              nextBoundary === undefined
                ? 0
                : Math.max(0, (p - nextBoundary + 0.025) / 0.025);
            stages.forEach((el, i) => {
              const alpha =
                i === index ? 1 - blend : i === index + 1 ? blend : 0;
              el.style.opacity = String(alpha);
              el.style.visibility = alpha > 0 ? "visible" : "hidden";
              el.inert = i !== index;
            });
            if (index !== previousIndex) {
              previousIndex = index;
              readouts.forEach((el) => {
                const visible = Number(el.dataset.readout) === index;
                el.style.opacity = visible ? "1" : "0";
                el.style.visibility = visible ? "visible" : "hidden";
              });
              chips.forEach((el, i) =>
                el.setAttribute("aria-current", i === index ? "step" : "false"),
              );
              if (scanner instanceof SVGElement)
                scanner.style.opacity =
                  index === 2 || index === 3 ? ".85" : "0";
              if (status)
                status.textContent =
                  [
                    "AWAITING INPUT",
                    "READING INPUT",
                    "SIGNAL EXTRACTION",
                    "RISK / DEMO",
                    "BUILDING CONTEXT",
                    "READY FOR REVIEW",
                  ][index] ?? "";
            }
            scene.dataset.progress = p.toFixed(4);
            scene.dataset.stage = String(index);
            setProgress(p);
            const reveal = Math.max(0, Math.min(1, (p - 0.66) / 0.18));
            setCaseOpacity(reveal);
            setCaseY((1 - reveal) * 35);
            if (caseReveal)
              caseReveal.style.visibility = reveal > 0 ? "visible" : "hidden";
            const machineScale = 1 - Math.max(0, p - 0.66) * 0.5;
            setScaleX(machineScale);
            setScaleY(machineScale);
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
            onRefresh: (self) => render(self.progress),
          });
          let active = true;
          const save = () => {
            try {
              sessionStorage.setItem(
                "sentinel-v2-story-progress",
                String(trigger.progress),
              );
            } catch {
              /* Storage may be disabled. */
            }
          };
          window.addEventListener("pagehide", save);
          const navigation = performance.getEntriesByType("navigation")[0] as
            PerformanceNavigationTiming | undefined;
          void document.fonts.ready.then(() => {
            if (!active) return;
            ScrollTrigger.refresh();
            if (
              navigation?.type === "reload" ||
              navigation?.type === "back_forward"
            ) {
              try {
                const saved = Number(
                  sessionStorage.getItem("sentinel-v2-story-progress") ?? 0,
                );
                if (Number.isFinite(saved)) {
                  trigger.scroll(
                    trigger.start +
                      Math.max(0, Math.min(1, saved)) *
                        (trigger.end - trigger.start),
                  );
                  ScrollTrigger.update();
                }
              } catch {
                /* Normal browser restoration remains available. */
              }
            }
            render(trigger.progress);
          });
          render(trigger.progress);
          return () => {
            active = false;
            window.removeEventListener("pagehide", save);
            scene
              .querySelectorAll<HTMLElement>("[data-story-stage]")
              .forEach((el) => {
                el.style.removeProperty("opacity");
                el.style.removeProperty("visibility");
                el.inert = false;
              });
          };
        },
      );
      return () => mm.revert();
    },
    { scope: root },
  );
  function goChapter(i: number) {
    const trigger = ScrollTrigger.getById("sentinel-evidence-reel");
    if (trigger)
      window.scrollTo({
        top:
          trigger.start +
          (trigger.end - trigger.start) * (boundaries[i] ?? 0) +
          1,
        behavior: "instant",
      });
    else document.getElementById(`v2-stage-${i}`)?.scrollIntoView();
  }
  function skip() {
    const end = document.getElementById("v2-after-story");
    end?.scrollIntoView({ behavior: "instant", block: "start" });
    end?.focus({ preventScroll: true });
  }
  return (
    <div ref={root} className="v2-story" data-progress="0" data-stage="0">
      <header className="v2-marketing-nav">
        <Link className="v2-wordmark" to="/__v2-preview">
          <span className="v2-brand-icon">S</span>SENTINEL
          <span className="v2-nav-edition">/ INTELLIGENCE, IN CONTEXT.</span>
        </Link>
        <nav aria-label="Preview navigation">
          <button onClick={skip}>Skip story</button>
          <Link to="/__v2-preview/dossier">
            Explore the workspace <ArrowUpRight size={15} />
          </Link>
        </nav>
      </header>
      <main>
        <div className="v2-story-track">
          <section className="v2-story-pin" aria-label="Evidence Reel story">
            <div className="v2-story-topline">
              <span>
                <span className="v2-dot" /> FORENSIC INTELLIGENCE / HUMAN
                DECISIONS
              </span>
              <span>
                SCROLL TO INVESTIGATE <ArrowDown size={13} />
              </span>
            </div>
            <div className="v2-hero-grid">
              <div className="v2-story-copy">
                {storyStages.map((s, i) => (
                  <section
                    key={s.step}
                    id={`v2-stage-${i}`}
                    data-story-stage
                    className={`v2-stage v2-stage-${i}`}
                  >
                    <p className="v2-eyebrow">
                      <span>{s.step}</span> / {s.label}
                    </p>
                    <h1>
                      {s.title}
                      <br />
                      <span>{s.subtitle}</span>
                    </h1>
                    <p className="v2-story-description">{s.text}</p>
                    <Link className="v2-button" to="/__v2-preview/dossier">
                      {i === 5
                        ? "Enter the demo workspace"
                        : "Explore the system"}{" "}
                      <ArrowUpRight size={17} />
                    </Link>
                    {i === 0 && (
                      <Link className="v2-text-link" to="/">
                        Open Command Center <ArrowRight size={14} />
                      </Link>
                    )}
                  </section>
                ))}
              </div>
              <div className="v2-visual">
                <div className="v2-visual-index">
                  <span>EVIDENCE TRANSPORT</span>
                  <span>ET—001</span>
                </div>
                <div className="v2-machine-wrap">
                  <Machine />
                </div>
                <div data-readout="1" className="v2-stage-readout">
                  <span className="v2-eyebrow">01 / SIMULATED TRANSACTION</span>
                  <strong>
                    $1,849.00 <small>USD</small>
                  </strong>
                  <p>
                    DEMO-0148 <span>CAPTURED · FIXTURE</span>
                  </p>
                </div>
                <div data-readout="2" className="v2-stage-readout">
                  <span className="v2-eyebrow">02 / ILLUSTRATIVE SIGNALS</span>
                  <p>
                    Amount vs merchant median <b>8.4×</b>
                  </p>
                  <p>
                    Payments · previous 24 hours <b>7</b>
                  </p>
                  <p>
                    New customer <b>Yes</b>
                  </p>
                </div>
                <div data-readout="3" className="v2-stage-readout">
                  <span className="v2-eyebrow">
                    03 / ILLUSTRATIVE ASSESSMENT
                  </span>
                  <strong className="v2-critical">
                    87 <small>/ 100 · HIGH RISK</small>
                  </strong>
                  <p>Simulated score · human review</p>
                </div>
                <div data-case-reveal className="v2-case-reveal">
                  <div>
                    <span className="v2-eyebrow">
                      INVESTIGATION PREVIEW / SIMULATED
                    </span>
                    <span>OPEN</span>
                  </div>
                  <strong>Evidence, assembled.</strong>
                  <p>
                    Payment context <span>→</span> Risk factors <span>→</span>{" "}
                    Human review
                  </p>
                </div>
                <div className="v2-visual-caption">
                  <span>PRECISION IN. CLARITY OUT.</span>
                  <span>ORIGINAL VECTOR CONSTRUCTION</span>
                </div>
              </div>
            </div>
            <footer className="v2-story-footer">
              <div className="v2-scroll-cue">
                <ChevronDown size={17} />
                <span>SCROLL TO FOLLOW THE EVIDENCE</span>
              </div>
              <nav aria-label="Story chapters">
                {storyStages.map((s, i) => (
                  <button
                    data-chapter
                    key={s.step}
                    onClick={() => goChapter(i)}
                    aria-label={`Go to ${s.label}`}
                    aria-current={i === 0 ? "step" : undefined}
                  >
                    <span>{s.step}</span>
                    <i />
                  </button>
                ))}
              </nav>
              <span>SIMULATED EXAMPLE / NOT LIVE INFERENCE</span>
            </footer>
            <div className="v2-progress-track" aria-hidden="true">
              <i data-progress />
            </div>
          </section>
        </div>
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
              The signal is only the beginning. Explore a working dossier with
              transaction context, an illustrative risk assessment, and a clear
              record of where the data comes from.
            </p>
            <Link className="v2-button" to="/__v2-preview/dossier">
              Open the Payment Dossier <ArrowUpRight size={18} />
            </Link>
            <Link className="v2-text-link" to="/__v2-preview/workspace">
              Inspect authorized records <ArrowRight size={15} />
            </Link>
          </div>
        </section>
      </main>
      <footer className="v2-final-footer">
        <span>SENTINEL / FORENSIC EDITORIAL</span>
        <span>LOCAL DESIGN PROTOTYPE · V2 / 01</span>
      </footer>
    </div>
  );
}
