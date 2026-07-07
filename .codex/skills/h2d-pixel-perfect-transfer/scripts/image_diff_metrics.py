#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from PIL import Image, ImageChops


def compare(a: Path, b: Path, diff: Path | None = None):
    im1 = Image.open(a).convert('RGBA')
    im2 = Image.open(b).convert('RGBA')
    w=max(im1.width, im2.width); h=max(im1.height, im2.height)
    bg=(255,255,255,0)
    c1=Image.new('RGBA',(w,h),bg); c2=Image.new('RGBA',(w,h),bg)
    c1.paste(im1,(0,0)); c2.paste(im2,(0,0))
    d=ImageChops.difference(c1,c2)
    bbox=d.getbbox()
    nonzero=0
    for px in d.getdata():
        if px != (0,0,0,0): nonzero+=1
    if diff:
        diff.parent.mkdir(parents=True, exist_ok=True)
        d.save(diff)
    return {'width':w,'height':h,'diff_bbox':list(bbox) if bbox else None,'different_pixels':nonzero,'total_pixels':w*h,'pixel_mismatch_ratio': nonzero/(w*h) if w*h else 0}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('original',type=Path); ap.add_argument('candidate',type=Path); ap.add_argument('--diff',type=Path); ap.add_argument('--out',type=Path)
    args=ap.parse_args(); res=compare(args.original,args.candidate,args.diff)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(res,indent=2),encoding='utf-8')
    print(json.dumps(res,indent=2))
if __name__=='__main__': main()
