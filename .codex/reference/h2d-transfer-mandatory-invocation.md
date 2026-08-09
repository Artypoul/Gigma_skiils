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

1. `create_transfer_contract.py` must freshly derive source/decoder hashes, responsive matrix, browser capabilities, candidate include closure, sidecars, lifecycle commands and expected reports.
2. `freeze_reference_bundle.py` accepts a pinned local runnable donor. Missing or changed artifacts, mismatched visual/dynamic donor identities and incomplete classification are non-pass.
3. Missing behavior/liveness reports never imply static scope. Truncation, unsupported interactive boundaries and runtime/action errors keep classification non-final.
4. Owner decisions require a verified signature or trusted owner-controlled event receipt. A local `approved: true`, reason or hash is not authorization.
5. `run_current_gates.py` regenerates evidence, proves every `viewport×profile` key, and re-hashes the candidate after report generation.
6. Direct `run_all_gates.py --output ...` verifies `current_evidence.json`; it cannot turn stale/manual reports into a pass. `--check-package` remains valid.
7. Final artifact readiness requires font, geometry/text-style, asset paint/provenance, frozen visual, behavior and liveness (when classified), `current_evidence`, and `validation_run` passes.
8. After feedback, rerun the full specialist matrix. The generic minimum «complained width plus adjacent breakpoint» is insufficient here.

Report `pass` maps to user-facing project status `ready`; incomplete proof is `partial`, `blocked`, or `unknown`, never a softened synonym.
