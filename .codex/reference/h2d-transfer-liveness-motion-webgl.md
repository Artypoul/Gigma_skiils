# Content liveness, animation and WebGL pipeline

This document defines how an agent captures and transfers runtime behavior that is invisible in a static H2D frame.

## v2.0 runtime evidence

- Any detected CSS animation/transition, RAF, timer-driven DOM update, canvas, WebGL or video surface makes liveness required unless a separately verified owner fallback exists.
- Canvas discovery instruments the application's actual `getContext` calls before load; the scanner never creates a context. Unobserved/unsupported canvas state is non-pass until the relevant reached state is classified.
- Every inventory trigger (including CSS hover/focus/checked), state and scroll/pointer trajectory is sampled on original and candidate with the same timeline.
- Every trace has at least three finite, non-negative, strictly increasing sample times starting at 0. Comparison checks each sample's position/size, transforms/styles, scoped frame pixels, canvas hashes and media playback time against the pinned original. Required video playback that cannot start and advance is non-pass.
- Rendering evidence pins browser/platform/font state and WebGL backend (or forces one software renderer). Nondeterministic clock/random inputs must be pinned or have a verified owner policy.
- Original traces live in the atomic reference bundle. `run_current_gates.py` captures only the current candidate and rejects changed/missing reference artifacts.

## Dynamic surfaces

Treat these as dynamic surfaces when they exist inside the transfer scope:

- CSS animation/transition.
- JS animation, requestAnimationFrame, timers.
- Scroll-linked motion, sticky, parallax.
- Canvas 2D.
- WebGL/WebGL2.
- Video/poster/playback.
- Lottie, GSAP, Three.js, Spline, Rive, Swiper, Pixi, Framer Motion.
- Counters, tickers, marquees, loaders and dynamic text.

## Required artifacts

- `reports/liveness_inventory.json`
- `reports/webgl_capture_report.json`
- `reports/original_animation_trace.jsonl`
- `reports/candidate_animation_trace.jsonl`
- `reports/liveness_validation.json`
- `screenshots/liveness/*` and `videos/liveness/*` when motion/video/WebGL evidence is needed.

## Pass rule

A dynamic surface passes only when the candidate reproduces the original trigger, timing, visual states and runtime evidence. Every inventoried WebGL canvas needs a `pass` capture with at least three frame hashes and non-blank samples; `not-present` and empty nominal passes fail. A static image clone fails for a critical WebGL/canvas/animation surface unless the user explicitly accepts `static-fallback`.
