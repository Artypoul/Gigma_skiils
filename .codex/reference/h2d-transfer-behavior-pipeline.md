# Behavior pipeline

1. `behavior_inventory.js` scans the original page for interactive controls.
2. `behavior_matrix_generate.js` converts inventory into reproducible interactions.
3. `behavior_capture_trace.js` records before/after semantic state and screenshots.
4. `behavior_build_state_targets.py` turns original traces into targets.
5. Candidate implements behavior and maps selectors in `behavior_implementation_map.json`.
6. Candidate traces are captured with the same matrix.
7. `behavior_compare_traces.py` fails on critical missing states.


## v1.7 note

Behavior covers interactions; liveness covers runtime motion/rendering. Use `h2d-transfer-liveness-motion-webgl.md` from the same reference bundle when the original has animation, canvas, WebGL, video or scroll-linked effects.
