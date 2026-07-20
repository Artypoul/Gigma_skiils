#!/usr/bin/env python3
"""Export a Segment Anything mask decoder to ONNX without importing heavy deps for --help."""

from __future__ import annotations

import argparse
import sys
from functools import partial
from pathlib import Path
from typing import Sequence


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the Segment Anything mask decoder to an ONNX model."
    )
    parser.add_argument("--checkpoint", type=Path, required=True, help="SAM checkpoint path")
    parser.add_argument(
        "--model-type",
        choices=("default", "vit_h", "vit_l", "vit_b"),
        default="vit_h",
        help="SAM checkpoint architecture (default: vit_h)",
    )
    parser.add_argument("--output", type=Path, required=True, help="Destination .onnx path")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset (default: 17)")
    parser.add_argument(
        "--return-single-mask",
        action="store_true",
        help="Return only the best mask instead of multimask output",
    )
    parser.add_argument(
        "--use-stability-score",
        action="store_true",
        help="Use stability scores when selecting a single mask",
    )
    parser.add_argument(
        "--gelu-approximate",
        action="store_true",
        help="Use tanh GELU approximation for runtimes that need it",
    )
    return parser.parse_args(argv)


def export_model(options: argparse.Namespace) -> None:
    if options.opset < 11:
        raise ValueError("--opset must be 11 or newer")
    if not options.checkpoint.is_file():
        raise FileNotFoundError(f"checkpoint not found: {options.checkpoint}")

    try:
        import torch
        from segment_anything import sam_model_registry
        from segment_anything.utils.onnx import SamOnnxModel
    except ImportError as exc:
        raise RuntimeError(
            "ONNX export requires torch and segment-anything. "
            "Install the dependencies documented by the skill before exporting."
        ) from exc

    if options.gelu_approximate:
        torch.nn.functional.gelu = partial(torch.nn.functional.gelu, approximate="tanh")

    sam = sam_model_registry[options.model_type](checkpoint=str(options.checkpoint))
    sam.to(device="cpu")
    sam.eval()
    onnx_model = SamOnnxModel(
        model=sam,
        return_single_mask=options.return_single_mask,
        use_stability_score=options.use_stability_score,
    )

    embed_dim = sam.prompt_encoder.embed_dim
    embed_height, embed_width = sam.prompt_encoder.image_embedding_size
    mask_input_size = (4 * embed_height, 4 * embed_width)
    dummy_inputs = {
        "image_embeddings": torch.randn(1, embed_dim, embed_height, embed_width),
        "point_coords": torch.randint(0, 1024, (1, 5, 2), dtype=torch.float),
        "point_labels": torch.randint(0, 4, (1, 5), dtype=torch.float),
        "mask_input": torch.randn(1, 1, *mask_input_size, dtype=torch.float),
        "has_mask_input": torch.tensor([1], dtype=torch.float),
        "orig_im_size": torch.tensor([1500, 2250], dtype=torch.float),
    }

    options.output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        onnx_model,
        tuple(dummy_inputs.values()),
        str(options.output),
        export_params=True,
        verbose=False,
        opset_version=options.opset,
        do_constant_folding=True,
        input_names=list(dummy_inputs),
        output_names=["masks", "iou_predictions", "low_res_masks"],
        dynamic_axes={
            "point_coords": {1: "num_points"},
            "point_labels": {1: "num_points"},
        },
    )


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_args(argv)
    try:
        export_model(options)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"exported={options.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
