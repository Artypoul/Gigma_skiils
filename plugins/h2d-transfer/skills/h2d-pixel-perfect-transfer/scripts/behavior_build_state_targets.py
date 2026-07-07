#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path


def read_jsonl(p: Path):
    return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--traces',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); args=ap.parse_args()
    targets=[]
    for t in read_jsonl(args.traces):
        before=t.get('before') or {}; after=t.get('after') or {}
        targets.append({'interaction_id':t.get('interaction_id'), 'component_id':t.get('component_id'), 'criticality':t.get('criticality','normal'), 'expected':{
            'exists': after.get('exists'),
            'url_changed': before.get('url') != after.get('url'),
            'aria_expanded': after.get('aria_expanded'),
            'controlled_visible': after.get('controlled_visible'),
            'body_overflow': after.get('body_overflow'),
            'active': after.get('active')
        }})
    out={'result':'pass' if targets else 'not-tested','targets':targets}
    args.out.parent.mkdir(parents=True,exist_ok=True); args.out.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8'); print(f'targets={len(targets)} out={args.out}')
if __name__=='__main__': main()
