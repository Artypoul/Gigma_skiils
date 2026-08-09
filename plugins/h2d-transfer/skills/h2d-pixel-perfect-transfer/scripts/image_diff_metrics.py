#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw


def compare(a: Path, b: Path, diff: Path | None = None, masks: list[dict] | None = None, regions: list[dict] | None = None):
    im1 = Image.open(a).convert('RGBA')
    im2 = Image.open(b).convert('RGBA')
    w=max(im1.width, im2.width); h=max(im1.height, im2.height)
    bg=(255,255,255,0)
    c1=Image.new('RGBA',(w,h),bg); c2=Image.new('RGBA',(w,h),bg)
    c1.paste(im1,(0,0)); c2.paste(im2,(0,0))
    d=ImageChops.difference(c1,c2)
    if masks:
        draw=ImageDraw.Draw(d)
        for mask in masks:
            x=int(mask['x']); y=int(mask['y']); width=int(mask['width']); height=int(mask['height'])
            draw.rectangle((x,y,x+width,y+height),fill=(0,0,0,0))
    bbox=d.getbbox()
    nonzero=0
    for px in d.getdata():
        if px != (0,0,0,0): nonzero+=1
    if diff:
        diff.parent.mkdir(parents=True, exist_ok=True)
        d.save(diff)
    region_results=[]
    for region in regions or []:
        x=max(0,int(region['x'])); y=max(0,int(region['y'])); right=min(w,x+int(region['width'])); bottom=min(h,y+int(region['height']))
        cropped=d.crop((x,y,right,bottom)); different=sum(1 for px in cropped.getdata() if px != (0,0,0,0)); total=max(0,right-x)*max(0,bottom-y); ratio=different/total if total else 0
        threshold=float(region.get('max_pixel_mismatch_ratio',0.0))
        region_results.append({'region_id':region.get('region_id'),'different_pixels':different,'total_pixels':total,'pixel_mismatch_ratio':ratio,'threshold':threshold,'result':'pass' if ratio<=threshold else 'fail'})
    return {'width':w,'height':h,'diff_bbox':list(bbox) if bbox else None,'different_pixels':nonzero,'total_pixels':w*h,'pixel_mismatch_ratio': nonzero/(w*h) if w*h else 0,'regions':region_results}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('original',type=Path); ap.add_argument('candidate',type=Path); ap.add_argument('--diff',type=Path); ap.add_argument('--out',type=Path); ap.add_argument('--masks',type=Path); ap.add_argument('--regions',type=Path)
    args=ap.parse_args(); masks=json.loads(args.masks.read_text(encoding='utf-8')) if args.masks else None; regions=json.loads(args.regions.read_text(encoding='utf-8')) if args.regions else None; res=compare(args.original,args.candidate,args.diff,masks,regions)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(res,indent=2),encoding='utf-8')
    print(json.dumps(res,indent=2))
if __name__=='__main__': main()
