# Contracts overview

The package uses one naming system across docs, schemas, templates and scripts.

Static scope requires `behavior_validation.json` with `result=static-scope` or `not-tested`.
Interactive scope requires full behavior artifacts. The final runner decides required behavior from CLI flag or from `behavior_validation.behavior_required`.


## Mandatory source and final gate

The runner must require `source_manifest.json` plus these files before final pass:

- `source/input.original`
- `source/input.h2d`
- `source/input.sha256`
- `source/h2d_decoded.json`
- `source/h2d_tree_index.json`

A transfer is not done until `python scripts/run_all_gates.py --output h2d-transfer-output --behavior-required auto` creates `reports/validation_run.json` with `result=pass`.


## v1.7 liveness contract

If `liveness_required=true`, the output contract includes `liveness_inventory`, `webgl_capture_report`, `original_animation_trace`, `candidate_animation_trace` and `liveness_validation`. If `liveness_required=false`, `liveness_validation.json` still exists and explains `static-scope` or `not-tested`.
