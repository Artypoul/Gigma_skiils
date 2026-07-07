# Mandatory Agent Invocation Contract v1.6

This file duplicates the hard gate from `SKILL.md` so agents that inspect the plugin `reference/` folder or the mirrored `.codex/reference/` folder cannot miss it.

```text
Перед переносом распакуй H2D через source intake.
После переноса обязательно прогони gates через scripts/run_all_gates.py.
Не писать "готово", пока не пройдены geometry, asset paint, live comparison, behavior validation и liveness/WebGL validation для интерактивных или динамических компонентов.
```

Operational meaning:

1. Start every task with source intake and H2D decode.
2. Do not build final HTML before `h2d_unpack_report.status == "ok"`.
3. Run `scripts/run_all_gates.py` after the last change.
4. `validation_run.json.result == "pass"` is the only final-ready condition.
5. `diff_summary.json.result == "pass"` is mandatory for final readiness.
6. Interactive scopes require `behavior_validation.json.result == "pass"`.


В v1.7 dynamic runtime content is mandatory-gated: animation, WebGL, canvas, video and scroll-linked effects require `liveness_validation.json.result == "pass"` before `готово`.
