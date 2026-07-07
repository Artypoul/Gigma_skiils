#!/usr/bin/env python3
"""Final mandatory gate runner for H2D transfer outputs and package self-checks."""
from __future__ import annotations
import argparse, hashlib, json, os, py_compile, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import jsonschema
except Exception:  # pragma: no cover
    jsonschema = None

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_BY_TEMPLATE = {
    'source_intake_template.json':'source_intake.schema.json',
    'source_manifest_template.json':'source_manifest.schema.json',
    'h2d_unpack_report_template.json':'h2d_unpack_report.schema.json',
    'decode_candidates_template.json':'decode_candidates.schema.json',
    'schema_discovery_template.json':'schema_discovery.schema.json',
    'tree_scope_template.json':'tree_scope.schema.json',
    'raw_asset_inventory_template.json':'raw_asset_inventory.schema.json',
    'rect_targets_template.json':'rect_targets.schema.json',
    'node_validation_template.json':'node_validation.schema.json',
    'asset_map_template.json':'asset_map.schema.json',
    'asset_bitmap_audit_template.json':'asset_bitmap_audit.schema.json',
    'asset_visibility_chain_template.json':'asset_visibility_chain.schema.json',
    'broken_asset_requests_template.json':'broken_asset_requests.schema.json',
    'asset_paint_validation_template.json':'asset_paint_validation.schema.json',
    'diff_summary_template.json':'diff_summary.schema.json',
    'behavior_inventory_template.json':'behavior_inventory.schema.json',
    'event_listener_inventory_template.json':'event_listener_inventory.schema.json',
    'interaction_matrix_template.json':'interaction_matrix.schema.json',
    'behavior_state_targets_template.json':'behavior_state_targets.schema.json',
    'behavior_implementation_map_template.json':'behavior_implementation_map.schema.json',
    'behavior_validation_template.json':'behavior_validation.schema.json',
    'behavior_validation_static_template.json':'behavior_validation.schema.json',
    'liveness_inventory_template.json':'liveness_inventory.schema.json',
    'webgl_capture_report_template.json':'webgl_capture_report.schema.json',
    'animation_trace_original_template.json':'animation_trace.schema.json',
    'animation_trace_candidate_template.json':'animation_trace.schema.json',
    'liveness_validation_template.json':'liveness_validation.schema.json',
    'liveness_validation_static_template.json':'liveness_validation.schema.json',
    'output_manifest_template.json':'output_manifest.schema.json',
    'output_contract_interactive_template.json':'output_contract.schema.json',
    'output_contract_static_template.json':'output_contract.schema.json',
    'validation_run_template.json':'validation_run.schema.json',
    'font_manifest_template.json':'font_manifest.schema.json',
}


def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding='utf-8'))

def validate_json(data: Any, schema_path: Path) -> list[str]:
    if jsonschema is None: return ['jsonschema not installed']
    try:
        jsonschema.Draft202012Validator(load_json(schema_path)).validate(data)
        return []
    except Exception as e:
        return [str(e).split('\n')[0]]

def check_package(pkg: Path) -> dict[str, Any]:
    checks=[]; issues=[]
    # schema/template validation
    for tmpl, schema in SCHEMA_BY_TEMPLATE.items():
        tp=pkg/'templates'/tmpl; sp=pkg/'schemas'/schema
        if not tp.exists() or not sp.exists():
            checks.append({'name':f'template:{tmpl}','result':'fail','message':'missing template or schema'}); issues.append(tmpl); continue
        errs=validate_json(load_json(tp), sp)
        checks.append({'name':f'template:{tmpl}','result':'pass' if not errs else 'fail','message':'; '.join(errs) if errs else 'valid'})
        issues.extend(errs)
    # python compile
    for py in sorted((pkg/'scripts').glob('*.py')):
        try:
            cfile = str(Path(tempfile.gettempdir()) / f'h2d_skill_check_{py.stem}.pyc')
            py_compile.compile(str(py), cfile=cfile, doraise=True)
            try:
                Path(cfile).unlink(missing_ok=True)
            except Exception:
                pass
            checks.append({'name':f'py_compile:{py.name}','result':'pass','message':'ok'})
        except Exception as e:
            checks.append({'name':f'py_compile:{py.name}','result':'fail','message':str(e)[:200]}); issues.append(str(e))
    # node syntax
    for js in sorted((pkg/'scripts').glob('*.js')):
        try:
            subprocess.run(['node','--check',str(js)], check=True, capture_output=True, text=True)
            checks.append({'name':f'node_check:{js.name}','result':'pass','message':'ok'})
        except Exception as e:
            checks.append({'name':f'node_check:{js.name}','result':'fail','message':str(e)[:200]}); issues.append(str(e))
    result='pass' if all(c['result']=='pass' for c in checks) else 'fail'
    return {'result':result,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'issues':issues}

def check_report(path: Path, schema_name: str, required_result: set[str]|None=None) -> tuple[dict[str,str], Any|None]:
    name=path.name; schema=ROOT/'schemas'/schema_name
    if not path.exists(): return {'name':name,'result':'fail','message':'missing'}, None
    try: data=load_json(path)
    except Exception as e: return {'name':name,'result':'fail','message':f'invalid json: {e}'}, None
    errs=validate_json(data,schema)
    if errs: return {'name':name,'result':'fail','message':'; '.join(errs)}, data
    if required_result and data.get('result') not in required_result:
        return {'name':name,'result':'fail','message':f"result={data.get('result')} not in {sorted(required_result)}"}, data
    return {'name':name,'result':'pass','message':'ok'}, data



def add_file_exists_check(checks: list[dict[str, str]], path: Path, label: str|None=None) -> None:
    ok = path.exists() and path.stat().st_size > 0
    checks.append({'name': label or str(path), 'result': 'pass' if ok else 'fail', 'message': 'exists' if ok else 'missing or empty'})

def add_h2d_unpack_strict_checks(checks: list[dict[str, str]], unpack_data: Any|None) -> None:
    if not isinstance(unpack_data, dict):
        checks.append({'name':'h2d_unpack_strict_status','result':'fail','message':'missing h2d_unpack_report data'})
        return
    status = unpack_data.get('status')
    verdict = unpack_data.get('source_unpack_verdict')
    checks.append({'name':'h2d_unpack_status_ok','result':'pass' if status == 'ok' else 'fail','message':f'status={status!r}'})
    checks.append({'name':'source_unpack_verdict_pass','result':'pass' if verdict == 'pass' else 'fail','message':f'source_unpack_verdict={verdict!r}'})

def add_live_comparison_strict_check(checks: list[dict[str, str]], diff_data: Any|None) -> None:
    if not isinstance(diff_data, dict):
        checks.append({'name':'live_comparison_result_pass','result':'fail','message':'missing diff_summary data'})
        return
    result = diff_data.get('result')
    checks.append({'name':'live_comparison_result_pass','result':'pass' if result == 'pass' else 'fail','message':f'diff_summary.result={result!r}; final ready requires pass'})

def add_liveness_strict_check(checks: list[dict[str, str]], liveness_data: Any|None, liveness_required: bool) -> None:
    if not isinstance(liveness_data, dict):
        checks.append({'name':'liveness_validation_result_pass','result':'fail','message':'missing liveness_validation data'})
        return
    result = liveness_data.get('result')
    if liveness_required:
        checks.append({'name':'liveness_validation_result_pass','result':'pass' if result == 'pass' else 'fail','message':f'liveness_validation.result={result!r}; dynamic/WebGL final ready requires pass'})
    else:
        checks.append({'name':'liveness_validation_static_or_pass','result':'pass' if result in {'static-scope','not-tested','pass'} else 'fail','message':f'liveness_validation.result={result!r}'})

def infer_behavior_required(out: Path, explicit: str) -> bool:
    if explicit in ('true','yes','1'): return True
    if explicit in ('false','no','0'): return False
    bv=out/'reports'/'behavior_validation.json'
    if bv.exists():
        try: return bool(load_json(bv).get('behavior_required'))
        except Exception: pass
    return (out/'reports'/'behavior_inventory.json').exists()

def infer_liveness_required(out: Path, explicit: str) -> bool:
    if explicit in ('true','yes','1'): return True
    if explicit in ('false','no','0'): return False
    lv=out/'reports'/'liveness_validation.json'
    if lv.exists():
        try: return bool(load_json(lv).get('liveness_required'))
        except Exception: pass
    inv=out/'reports'/'liveness_inventory.json'
    if inv.exists():
        try:
            data=load_json(inv)
            return bool(data.get('liveness_required')) or bool(data.get('surfaces'))
        except Exception: pass
    return False

def check_output(out: Path, behavior_required_arg: str, liveness_required_arg: str='auto') -> dict[str, Any]:
    checks=[]; issues=[]; reports=out/'reports'
    behavior_required=infer_behavior_required(out, behavior_required_arg)
    liveness_required=infer_liveness_required(out, liveness_required_arg)
    required=[
        ('source_intake.json','source_intake.schema.json',None),
        ('source_manifest.json','source_manifest.schema.json',None),
        ('h2d_unpack_report.json','h2d_unpack_report.schema.json',None),
        ('raw_asset_inventory.json','raw_asset_inventory.schema.json',None),
        ('decode_candidates.json','decode_candidates.schema.json',None),
        ('schema_discovery.json','schema_discovery.schema.json',None),
        ('rect_targets.json','rect_targets.schema.json',None),
        ('asset_map.json','asset_map.schema.json',None),
        ('asset_bitmap_audit.json','asset_bitmap_audit.schema.json',{'pass','manual-review'}),
        ('asset_visibility_chain.json','asset_visibility_chain.schema.json',{'pass'}),
        ('broken_asset_requests.json','broken_asset_requests.schema.json',{'pass'}),
        ('asset_paint_validation.json','asset_paint_validation.schema.json',{'pass'}),
        ('node_validation.json','node_validation.schema.json',{'pass'}),
        ('diff_summary.json','diff_summary.schema.json',{'pass'}),
        ('behavior_validation.json','behavior_validation.schema.json',{'pass'} if behavior_required else {'static-scope','not-tested','pass'}),
        ('liveness_validation.json','liveness_validation.schema.json',{'pass'} if liveness_required else {'static-scope','not-tested','pass'}),
        ('output_manifest.json','output_manifest.schema.json',{'pass'}),
    ]
    if behavior_required:
        required += [
            ('behavior_inventory.json','behavior_inventory.schema.json',{'pass','partial'}),
            ('interaction_matrix.json','interaction_matrix.schema.json',{'pass','partial'}),
            ('event_listener_inventory.json','event_listener_inventory.schema.json',{'pass','partial'}),
            ('behavior_state_targets.json','behavior_state_targets.schema.json',{'pass','partial'}),
            ('behavior_implementation_map.json','behavior_implementation_map.schema.json',{'pass','partial'}),
        ]
        for fn in ['original_behavior_traces.jsonl','candidate_behavior_traces.jsonl']:
            p=reports/fn; ok=p.exists() and p.stat().st_size>0; checks.append({'name':fn,'result':'pass' if ok else 'fail','message':'exists' if ok else 'missing or empty'})
    if liveness_required:
        required += [
            ('liveness_inventory.json','liveness_inventory.schema.json',{'pass','partial'}),
            ('webgl_capture_report.json','webgl_capture_report.schema.json',{'pass','partial','not-present','manual-review'}),
        ]
        for fn in ['original_animation_trace.jsonl','candidate_animation_trace.jsonl']:
            p=reports/fn; ok=p.exists() and p.stat().st_size>0; checks.append({'name':fn,'result':'pass' if ok else 'fail','message':'exists' if ok else 'missing or empty'})
    # Mandatory source-intake files. These prove the agent unpacked H2D before transfer.
    source_dir = out/'source'
    for rel in ['input.original','input.h2d','input.sha256','h2d_decoded.json','h2d_tree_index.json']:
        add_file_exists_check(checks, source_dir/rel, f'source/{rel}')
    unpack_data = None
    diff_data = None
    liveness_data = None
    for fn, schema, allowed in required:
        c,d=check_report(reports/fn,schema,allowed); checks.append(c)
        if fn == 'h2d_unpack_report.json': unpack_data = d
        if fn == 'diff_summary.json': diff_data = d
        if fn == 'liveness_validation.json': liveness_data = d
    add_h2d_unpack_strict_checks(checks, unpack_data)
    add_live_comparison_strict_check(checks, diff_data)
    add_liveness_strict_check(checks, liveness_data, liveness_required)
    # Review file
    review=reports/'review.md'; checks.append({'name':'review.md','result':'pass' if review.exists() and review.stat().st_size>0 else 'fail','message':'ok' if review.exists() else 'missing'})
    result='pass' if all(c['result']=='pass' for c in checks) else 'needs-fix'
    issues=[c for c in checks if c['result']!='pass']
    return {'result':result,'behavior_required':behavior_required,'liveness_required':liveness_required,'checked_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'issues':issues}

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--check-package',type=Path); ap.add_argument('--output',type=Path); ap.add_argument('--behavior-required',default='auto',choices=['auto','true','false','yes','no','1','0']); ap.add_argument('--liveness-required',default='auto',choices=['auto','true','false','yes','no','1','0']); ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    if args.check_package:
        res=check_package(args.check_package)
        out=args.out or (Path(tempfile.gettempdir())/'h2d-transfer-package-validation.json')
    elif args.output:
        res=check_output(args.output,args.behavior_required,args.liveness_required)
        out=args.out or args.output/'reports'/'validation_run.json'
    else:
        ap.error('Use --check-package or --output')
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(res,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f"result={res['result']} checks={len(res['checks'])} out={out}")
    return 0 if res['result']=='pass' else 2
if __name__=='__main__': raise SystemExit(main())
