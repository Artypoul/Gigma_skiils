#!/usr/bin/env python3
"""Compare liveness traces. This is a semantic gate, not a full optical-flow engine."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

def read_jsonl(p: Path):
    if not p.exists(): return []
    rows=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if line: rows.append(json.loads(line))
    return rows

def load_json(p: Path): return json.loads(p.read_text(encoding='utf-8'))

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--original',type=Path,required=True); ap.add_argument('--candidate',type=Path,required=True); ap.add_argument('--inventory',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    inv=load_json(args.inventory); orig={r.get('surface_id'):r for r in read_jsonl(args.original)}; cand={r.get('surface_id'):r for r in read_jsonl(args.candidate)}
    checks=[]; issues=[]
    for surf in inv.get('surfaces',[]):
        sid=surf.get('surface_id'); kind=surf.get('kind'); critical=surf.get('criticality')=='critical'
        o=orig.get(sid); c=cand.get(sid)
        if not o or not c:
            res='fail' if critical else 'partial'; msg='missing original or candidate trace'
        else:
            o_samples=o.get('samples',[]); c_samples=c.get('samples',[])
            o_hashes=[x.get('frame_hash') for x in o_samples]; c_hashes=[x.get('frame_hash') for x in c_samples]
            c_transforms=[(x.get('computed') or {}).get('transform') for x in c_samples]
            o_transforms=[(x.get('computed') or {}).get('transform') for x in o_samples]
            candidate_changes = len(set(filter(None,c_hashes)))>1 or len(set(filter(None,c_transforms)))>1
            original_changes = len(set(filter(None,o_hashes)))>1 or len(set(filter(None,o_transforms)))>1
            if original_changes and not candidate_changes and critical:
                res='fail'; msg='original changes over time but candidate trace is static'
            elif len(c_samples) < max(1, len(o_samples)//2):
                res='partial'; msg='candidate has insufficient samples'
            else:
                res='pass'; msg='trace evidence present'
        checks.append({'surface_id':sid,'kind':kind,'result':res,'message':msg,'evidence':['original_animation_trace.jsonl','candidate_animation_trace.jsonl']})
        if res not in ('pass',): issues.append({'surface_id':sid,'kind':kind,'result':res,'message':msg})
    liveness_required=bool(inv.get('liveness_required')) or any(s.get('criticality')=='critical' for s in inv.get('surfaces',[]))
    if not inv.get('surfaces'):
        result='static-scope'; webgl='not-present'
    elif any(c['result']=='fail' for c in checks):
        result='fail'; webgl='fail' if any(c.get('kind') in ('webgl','webgl2') and c['result']=='fail' for c in checks) else 'partial'
    elif any(c['result']=='partial' for c in checks):
        result='partial'; webgl='partial'
    else:
        result='pass'; webgl='pass' if any(c.get('kind') in ('webgl','webgl2') for c in checks) else 'not-present'
    report={'result':result,'liveness_required':liveness_required,'checked_at':datetime.now(timezone.utc).isoformat(),'webgl_runtime_verdict':webgl,'checks':checks,'accepted_deviations':[],'issues':issues}
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f"result={result} checks={len(checks)} out={args.out}")
    return 0 if result in ('pass','static-scope') else 2
if __name__ == '__main__': raise SystemExit(main())
