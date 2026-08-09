# Mandatory Agent Invocation Contract v1.8

This file duplicates the hard gate from `SKILL.md` so agents that inspect the plugin `reference/` folder or the mirrored `.codex/reference/` folder cannot miss it.

```text
Перед переносом распакуй H2D через source intake.
Порядок работы: сначала типографика и контейнеры, только потом блоки.
Геометрию воспроизводить структурой донора, а не компенсациями (spacer, scale(1.00…), дробные сдвиги).
Отчёты порождаются скриптами; отчёт, написанный руками ради прохождения схемы, — провал гейта.
Если свой текст не влезает в геометрию донора — остановиться и спросить владельца, а не сокращать молча.
После переноса обязательно прогони gates через scripts/run_all_gates.py.
Не писать "готово", пока не пройдены font, geometry + text styles, asset paint, asset provenance, live comparison, behavior validation и liveness/WebGL validation для интерактивных или динамических компонентов.
```

Operational meaning:

1. Start every task with source intake and H2D decode.
2. Do not build final HTML before `h2d_unpack_report.status == "ok"`.
3. Do not build block markup before `font_manifest.json` is `font-exact` or `font-substituted`.
4. Run `scripts/run_all_gates.py` after the last change.
5. `validation_run.json.result == "pass"` is the only final-ready condition.
6. `node_validation.json.result == "pass"` covers rects **and** text metrics; a font-family difference is a warning that must be documented in the font manifest.
7. `asset_provenance.json.result == "pass"` is mandatory: donor-derived assets need a declared brand status, and third-party brand content or anything over 1 MB needs a recorded owner decision.
8. `diff_summary.json.result == "pass"` is mandatory for final readiness, unless the live original demonstrably drifted from the snapshot **and** the owner confirmed the snapshot stays the reference — then rerun with `--accept-changed-source`.
9. Interactive scopes require `behavior_validation.json.result == "pass"`.

В v1.7 dynamic runtime content is mandatory-gated: animation, WebGL, canvas, video and scroll-linked effects require `liveness_validation.json.result == "pass"` before `готово`.

В v1.8 добавлены typography-first, no-compensation, generated-reports, content-divergence и asset-provenance правила, а также owner-confirmed выход из `changed-source`.
