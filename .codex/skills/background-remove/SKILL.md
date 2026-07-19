---
name: background-remove
description: >
  Remove backgrounds from images using AI. Triggers include:
  "remove background", "transparent background", "cut out", "isolate subject",
  "remove bg", "make transparent", "extract subject", "background removal"
  Creates PNG or WebP images with transparent backgrounds.
---

# Background Remove Skill

Remove backgrounds from images using AI (rembg/U2-Net) or built-in methods.

**Output:** PNG or WebP with transparent background.

## Identity-lock boundary

Background removal estimates a mask; it is not a face-preserving repositioning tool. If the request includes “не менять лица”, “без изменения лица”, “точно перенести”, or moving a person within the frame, do not use generation or inpainting. First produce and visually check a cutout; then route only a verified RGBA cutout to `$pixel-mask-move`. A flattened JPG or fully opaque PNG cannot be safely repositioned without re-rendering pixels.

## Quick Examples

| User Says | What Happens |
|-----------|--------------|
| "Remove the background from this photo" | AI removes background, outputs PNG |
| "Make this image transparent" | Removes background, preserves subject |
| "Cut out the product from this image" | Isolates subject with clean edges |
| "Remove backgrounds from all images in /photos" | Batch processes multiple images |
| "Quick background removal, white background" | Uses fast built-in method |

## Prerequisites

- `rembg` - AI-based background removal (recommended)
  ```bash
  pip install rembg
  # Or with GPU acceleration (faster, requires CUDA)
  pip install rembg[gpu]
  ```

- `Pillow` - Required for image processing
  ```bash
  pip install Pillow
  ```

The first run will download the U2-Net model (~170MB) which is cached for future use.

## Methods

| Method | Description | Best For |
|--------|-------------|----------|
| **rembg** | AI-based using U2-Net model | Complex images, photos, products (default) |
| **builtin** | White-to-transparent conversion | Icons, graphics with clean white backgrounds |

## Workflow

### Step 1: Gather Requirements (REQUIRED)

Use the `AskUserQuestion` tool for each question. Ask ONE question at a time.

**Q1: Image Source**
> "Which image(s) should I remove the background from?
>
> Please provide the file path or paste the image."

*Wait for response.*

**Q2: Method (Optional)**
> "Which removal method?
>
> - **AI** (rembg) - Best quality, works on any image (default)
> - **Built-in** - Faster, best for white backgrounds"

*Wait for response. Default to AI if user doesn't specify.*

**Q3: Output Location (Optional)**
> "Where should I save the result?
>
> - Same location with `_nobg` suffix (default)
> - Custom path"

*Wait for response.*

### Step 2: Execute Background Removal

**Quality guardrail:** Do not use a one-click mask as final output when the subject contains white or very light clothing against a white/light background. In this case, a segmentation model is only a *proposal*; neither thresholding alpha nor filling regions based on colour is permitted. Render on grey, dark and saturated backgrounds, then run `$pixel-mask-move/scripts/source_matte_qc.py` against the untouched source. A red candidate is a manual-review item, not an instruction to erase it. For a later face-locked move, both this review and `$pixel-mask-move/scripts/alpha_qc.py` must pass.

**Best available source:** If a matching empty-background frame exists from the same studio/camera position, use reference-background matting instead of one-click removal. If there is no background plate, use SAM only to establish the coarse silhouette, refine the uncertain edge manually, and keep the original RGB intact. Do not promise a clean transparent result from a white-on-white flattened photo until those checks are reviewed.

**Single image:**
```bash
python3 ${SKILL_PATH}/skills/background-remove/scripts/background_remove.py \
  -i "/path/to/image.jpg" \
  -o "/path/to/output.png"
```

**Batch processing:**
```bash
python3 ${SKILL_PATH}/skills/background-remove/scripts/background_remove.py \
  -i "/path/to/img1.jpg" "/path/to/img2.png" "/path/to/img3.webp" \
  -o "/path/to/output_folder"
```

**Using built-in method (faster for white backgrounds):**
```bash
python3 ${SKILL_PATH}/skills/background-remove/scripts/background_remove.py \
  -i "/path/to/icon.png" \
  -m builtin
```

### Step 3: Deliver Result

1. Show the result to the user
2. Confirm the background was removed successfully
3. Offer to:
   - Process additional images
   - Try a different method if quality isn't satisfactory
   - Adjust output format (PNG vs WebP)

## Script Parameters

| Parameter | Short | Description | Default |
|-----------|-------|-------------|---------|
| `--input` | `-i` | Input image path(s) | Required |
| `--output` | `-o` | Output path or directory | Auto-generated with `_nobg` suffix |
| `--method` | `-m` | Removal method (rembg, builtin) | rembg |

## Output Formats

The output format is determined by the file extension:

| Extension | Format | Notes |
|-----------|--------|-------|
| `.png` | PNG | Best quality, larger file (default) |
| `.webp` | WebP | Good compression, modern format |

## Integration with Other Skills

This skill can be called by other skills that need background removal:

### From Python (import)
```python
import sys
sys.path.insert(0, "${SKILL_PATH}/skills/background-remove/scripts")
from background_remove import remove_background

result = remove_background("/path/to/image.png", "/path/to/output.png", method="rembg")
if result.get("success"):
    print(f"Saved to: {result['file']}")
else:
    print(f"Error: {result['error']}")
```

### From Command Line
```bash
python3 ${SKILL_PATH}/skills/background-remove/scripts/background_remove.py \
  -i "/path/to/image.png" \
  -o "/path/to/output.png" \
  -m rembg
```

## Error Handling

**rembg not installed:**
```
rembg not installed. Install with: pip install rembg[gpu] (or pip install rembg for CPU-only)
```
The script will automatically fall back to the built-in method.

**Image not found:**
```
Image not found: /path/to/image.png
```

**Processing failed:**
- Try a different method
- Check if the image file is corrupted
- Ensure sufficient memory for large images

## Tips for Best Results

1. **Use rembg for photos** - AI handles complex edges (hair, fur, transparent objects)
2. **Use builtin for graphics** - Faster for icons/logos with clean white backgrounds
3. **Check edges** - If edges are rough, the AI method usually gives better results
4. **Batch process** - Process multiple images at once for efficiency
5. **GPU acceleration** - Install `rembg[gpu]` for faster processing on NVIDIA GPUs

## Examples

### Remove background from a photo
```bash
python3 ${SKILL_PATH}/skills/background-remove/scripts/background_remove.py \
  -i "product_photo.jpg" \
  -o "product_transparent.png"
```

### Batch process a folder
```bash
python3 ${SKILL_PATH}/skills/background-remove/scripts/background_remove.py \
  -i photos/*.jpg \
  -o "transparent_photos/"
```

### Fast removal for icons (white background)
```bash
python3 ${SKILL_PATH}/skills/background-remove/scripts/background_remove.py \
  -i "icon.png" \
  -m builtin
```

### Output as WebP (smaller file size)
```bash
python3 ${SKILL_PATH}/skills/background-remove/scripts/background_remove.py \
  -i "photo.jpg" \
  -o "result.webp"
```
