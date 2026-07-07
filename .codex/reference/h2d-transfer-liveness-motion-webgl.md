# Content liveness, animation and WebGL pipeline

This document defines how an agent captures and transfers runtime behavior that is invisible in a static H2D frame.

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

A dynamic surface passes only when the candidate reproduces the original trigger, timing, visual states and runtime evidence. A static image clone fails for a critical WebGL/canvas/animation surface unless the user explicitly accepts `static-fallback`.
