from __future__ import annotations

import argparse

from datasets.msr import MSRAction3D
from models.sequence_classification import MSRAction


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-path",
        required=True,
        help="Path to MSRAction3D dataset",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=35,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    dataset = MSRAction3D(args.dataset_path)
    model = MSRAction()
    print(dataset, model, args.epochs)


if __name__ == "__main__":
    main()