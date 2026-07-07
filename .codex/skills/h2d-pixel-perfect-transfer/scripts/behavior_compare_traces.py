#!/usr/bin/env python3
"""Compare original/candidate behavior traces. Critical mismatches fail."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--original',type=Path,required=True); ap.add_argument('--candidate',type=Path,required=True); ap.add_argument('--targets',type=Path); ap.add_argument('--out',type=Path,required=True); args=ap.parse_args()
    orig={t.get('interaction_id'):t for t in read_jsonl(args.original)}
    cand={t.get('interaction_id'):t for t in read_jsonl(args.candidate)}
    issues=[]; comps=[]
    for iid, o in orig.items():
        c=cand.get(iid); critical=o.get('criticality')=='critical'
        if not c:
            issues.append({'type':'missing-candidate-state','interaction_id':iid,'severity':'fail' if critical else 'partial'}); continue
        checks={}
        for field in ['exists','aria_expanded','controlled_visible','body_overflow']:
            ov=(o.get('after') or {}).get(field); cv=(c.get('after') or {}).get(field)
            if ov is None and cv is None: continue
            checks[field]='pass' if ov==cv else 'fail'
        # URL behavior: changed vs unchanged, not exact URL unless provided by spec.
        ourl=(o.get('before') or {}).get('url') != (o.get('after') or {}).get('url')
        curl=(c.get('before') or {}).get('url') != (c.get('after') or {}).get('url')
        checks['url_changed']='pass' if ourl==curl else 'fail'
        if o.get('error') and not c.get('error'): checks['original_error']='manual-review'
        fail=any(v=='fail' for v in checks.values())
        if fail:
            issues.append({'type':'semantic-mismatch','interaction_id':iid,'severity':'fail' if critical else 'partial','checks':checks})
        comps.append({'interaction_id':iid,'result':'fail' if fail else 'pass','checks':checks})
    for iid in sorted(set(cand)-set(orig)):
        issues.append({'type':'extra-candidate-state','interaction_id':iid,'severity':'fail' if (cand[iid].get('criticality')=='critical') else 'partial'})
    if any(i.get('severity')=='fail' for i in issues): result='fail'
    elif issues: result='partial'
    else: result='pass'
    out={'result':result,'behavior_required':True,'comparisons':comps,'accepted_deviations':[],'issues':issues,'safe_boundaries':[{'interaction_id':t.get('interaction_id'),'safe_boundary_applied':t.get('safe_boundary_applied',False)} for t in orig.values() if t.get('safe_boundary_applied')]}
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8'); print(f'behavior={result} comparisons={len(comps)} issues={len(issues)} out={args.out}')
    return 0 if result=='pass' else 2
if __name__=='__main__': raise SystemExit(main())
