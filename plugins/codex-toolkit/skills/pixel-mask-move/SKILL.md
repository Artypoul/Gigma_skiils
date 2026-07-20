---
name: pixel-mask-move
description: Deterministically move a verified RGBA cutout using a mask, without regeneration, scaling, retouching, or changing any source face pixels. Use for requests such as "move the guitarist closer" only when pixel fidelity and face identity must be preserved.
---

# Pixel Mask Move

This is an **identity-lock** skill: it moves existing pixels only. Never call image generation, inpainting, face restoration, resizing, or any tool that re-renders the image. A generated edit can look similar but cannot guarantee unchanged faces.

## Mandatory admission gate

Use this skill only if all conditions are true:

1. The source is an RGBA PNG with a real transparent area around the cutout; a flattened JPG/opaque PNG is not a layer.
2. `scripts/alpha_qc.py` returns `PASS` and its grey, dark, and colour preview shows no transparent clothing, hair, glasses, skin, instrument, or pale edge halo.
3. When the source was shot on a light/white background, `scripts/source_matte_qc.py` has been run against the untouched source. A `FAIL` means human review is mandatory; never discard its red candidates by colour.
4. A precise, hand-checked grayscale mask exists. The selected subject must not include another person.
5. The requested move does not require revealing pixels previously covered by a person or object.

If any condition fails, stop. Ask for a clean isolated cutout, original layered file, or a new photo. Do not replace missing pixels with a generative edit and do not describe a generated result as face-preserved.

## Workflow

1. Preserve the input file. Write a new output filename.
2. If an AI background-removal tool produced the alpha mask, first run `scripts/restore_source_rgb.py` with the untouched flat source and the cutout. This restores the original photographed RGB wherever alpha is visible; the mask remains the only editable data.
3. Run `scripts/alpha_qc.py` first. A `FAIL` is a hard stop. In particular, `light_edge_halo` means white/studio-background pixels remain in a soft edge: refine the mask manually instead of compositing it on a dark poster.
4. For a light/white studio background, run `scripts/source_matte_qc.py` before any move. It compares source colours only to *flag* interior background-like regions. It never repairs them. Inspect the red overlay and correct the mask manually. White shirts, collars and sneakers are not valid grounds for automatic fill or automatic deletion.
5. Use a hand-checked grayscale mask aligned to the RGBA source. White selects the object; black keeps the rest. Never classify a white patch as clothing from colour alone. Automatic subject selection is intentionally excluded: it can select hair, an instrument, or a neighbouring person incorrectly.
6. Run `scripts/move_masked_layer.py` with integer `--dx` and `--dy` values. Negative `dx` moves left; negative `dy` moves up. It repeats the alpha/halo gate and verifies pixels outside the old/new layer regions were not changed.
7. Use `--layer-order behind` when the moved person should tuck naturally behind another person. Use the default `front` order only when the user explicitly accepts the moved subject appearing in front. The default safety check stops a front overlap rather than corrupting an overlap.
8. Run `scripts/alpha_qc.py` on the output and inspect its three-background preview before handing off the PNG. Confirm there is no remaining original copy, no clipped hair/instrument, no unintended overlap, and no light fringe on the dark panel.

Example:

```powershell
python scripts/move_masked_layer.py `
  --input "group.png" --mask "guitarist_mask.png" --dx -60 --output "group_guitarist_closer.png" `
  --preview "group_guitarist_closer_preview.jpg"
```

## Limits

This moves existing pixels only. It cannot reveal pixels hidden behind an overlapping person, restore RGB pixels lost by a bad alpha mask, remove a halo baked into the input image, or turn a flattened photo into a trustworthy layer. In any of these cases, stop and ask for a clean original/layered source instead of generating replacement pixels.

## Quality gate

Run:

```powershell
python scripts/alpha_qc.py --input "cutout.png" --preview "cutout_qc.jpg"
```

The script flags suspicious transparent holes. Treat a `FAIL` result as a hard stop. The preview must be inspected on grey, dark and saturated backgrounds; a checkerboard alone can hide a white or dark halo.

For a cutout produced from a flat source, lock its visible RGB back to the source before QC:

```powershell
python scripts/restore_source_rgb.py `
  --source "group_original.png" --cutout "group_masked.png" --output "group_source_locked.png"
```

For a light source background, also require this evidence preview (dark, magenta, and red candidate overlay):

```powershell
python scripts/source_matte_qc.py `
  --source "group_original.png" --cutout "group_source_locked.png" `
  --preview "group_source_matte_qc.png"
```
