# Evidence Reel — prototype motion contract

Source: `src/preview/Story.tsx`, `Machine.tsx` and `preview.css` under apps/web. One GSAP ScrollTrigger, ID `sentinel-evidence-reel`, scoped by useGSAP/matchMedia. Desktop above 900px with normal motion pins one scene for four viewport-heights of travel (five viewport-heights including the visible scene). No duplicate hero, snapping, wheel handlers, audio, autoplay or global smooth scrolling.

Stages: idle 0–.14; arrival .14–.30; signals .30–.48; risk .48–.66; assembly .66–.84; reveal .84–1. Text crossfades over the .025 interval approaching the next stage. Inactive text is inert. Machine readouts and case context are deterministic, explicitly simulated. Phase 2 still needs the polished full-workspace transformation, richer evidence composition and final cinematic refinement; the prototype proves the interaction and design direction.

Shared distance: `d = clamp((p-.14)/.70, 0, 1) * 2000` SVG units. Both spools rotate `d/78` radians, a constant apparent transport radius approximation. The tape dash offset is `-d`. Reels begin/stall together and rewind identically. The illustration uses two equally sized apparent spools; changing wound-tape radius is intentionally omitted at prototype fidelity. No unrelated autoplay rotations.

`p` is ScrollTrigger progress. `scrub:true` and direct rendering make settled transforms deterministic from p. GSAP updates transforms/opacity and small diagnostics outside React state, so scrolling does not trigger component renders. Case reveal, scanner and risk/readout visibility share p. The reverse test compares the exact transform at the same settled checkpoint, not just CSS class names.

Fonts-ready refresh and invalidateOnRefresh handle geometry. React StrictMode/remount cleanup removes the trigger, pin spacer, matchMedia context and pagehide listener. A pagehide handler saves normalized progress to sessionStorage. Reload/history navigation restores that value after fonts/scene mounting because lazy Suspense can otherwise clamp native restoration before the pinned section exists. Ordinary route entry starts at the current browser position; no persistent autoplay state is introduced. Storage failures fall back safely to browser behavior.

`Skip story` scrolls past the pin and focuses the following section without trapping focus. Chapter buttons use the same normalized coordinates. Above-scene navigation scrolls normally out of view; chapter navigation and final CTA remain usable.

At <=900px or with prefers-reduced-motion, no pin/scroll instance is created. A stationary machine and all six readable stages form an ordinary vertical sequence. There are no essential hover-only actions. Returning to desktop creates one fresh context; resize is tested separately from mobile emulation. This is the chosen prototype mobile alternative, not a claim of physical-device testing.

Demo numbers are authored fixtures; actual model signals exist in `app/services/risk/features.py`: amount_vs_merchant_median, cust_txn_count_24h and is_new_customer. No device fingerprint, geolocation or identity graph is claimed.
