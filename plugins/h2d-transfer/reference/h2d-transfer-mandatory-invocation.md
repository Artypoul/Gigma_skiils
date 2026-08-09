# Mandatory Agent Invocation Contract v2.0

This duplicates the hard gate from `SKILL.md` so installed and mirrored agents cannot miss it.

```text
Перед переносом заново декодируй pinned H2D штатным decoder и создай immutable transfer contract.
Не переписывай viewport-ы из имени файла: обязательны все decoded widths, breakpoint boundaries, interval probes и browser profiles.
До правки кандидата заморозь один atomic reference bundle; visual и dynamic evidence обязаны иметь один donor identity.
Offline и live donor запускаются только в deny-by-default browser sandbox. Generic Playwright screenshot не заменяет specialist gates.
Порядок реализации: typography → container chain → blocks. Не компенсируй ошибочную структуру scale/translate/spacer/magic offsets.
После последней правки запускай scripts/run_current_gates.py, а не проверку старых reports.
Не писать «готово», пока current_evidence и validation_run не имеют result=pass на полной матрице.
```

Operational meaning:

1. `derive_reference_matrix.py` and `create_transfer_contract.py` must freshly derive source/decoder hashes and the responsive matrix. Breakpoints are accepted only from the bundled classification; the final reference is recaptured on every decoded/breakpoint/interval viewport and browser profile.
2. `freeze_reference_bundle.py` accepts a pinned local runnable donor, hashes its transitive resource closure (including interaction-loaded local resources) and generates classification across reachable states. Missing or changed resources, mismatched visual/dynamic donor identities and incomplete classification are non-pass.
3. Missing behavior/liveness reports never imply static scope. Truncation, delegated global listeners, unsupported interactive boundaries and runtime/action errors keep classification non-final. Structural ARIA roles alone do not invent interactions; timers make liveness required.
4. Owner decisions require a verified signature or trusted owner-controlled event receipt. A local `approved: true`, reason or hash is not authorization.
5. `run_current_gates.py` resolves every executable and file argument from its exact current/lifecycle cwd, quarantines every old expected report, regenerates and hashes the final source/decode copies, proves every `viewport×profile` key from passing individual gate rows, and re-hashes the candidate after report generation. Managed URL mode must own a previously unused loopback origin and serve a build identity bound to the current source/candidate closure.
6. Direct `run_all_gates.py --output ...` verifies `current_evidence.json`; it cannot turn stale/manual reports into a pass. `--check-package` remains valid.
7. Required behavior/liveness inventories, mappings and matrix rows must be complete `pass` artifacts. `partial`, `manual-review`, `not-tested` and `static-scope` are non-final diagnostics. Candidate replay must use the injective implementation map for every step; comparison covers before and after semantics.
8. Dynamic reference evidence is accepted only from `finalize_dynamic_reference.py`: every classification-required role must contain non-empty hashed artifacts for the complete matrix. Motion needs a valid 3+ sample timeline, per-sample rect/pixel/runtime comparison, advancing required video, and complete WebGL capture.
9. Final artifact readiness requires font, geometry/text-style, asset paint/provenance, frozen visual, behavior and liveness (when classified), `current_evidence`, and `validation_run` passes.
10. After feedback, rerun the full specialist matrix. The generic minimum «complained width plus adjacent breakpoint» is insufficient here.

Report `pass` maps to user-facing project status `ready`; incomplete proof is `partial`, `blocked`, or `unknown`, never a softened synonym.
