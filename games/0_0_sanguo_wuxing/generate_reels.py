#!/usr/bin/env python3
"""生成 M2a 已调优的 7 条确定性 reel strip。"""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path


COUNTS_PER_REEL = {
    "H1": 20,
    "H2": 28,
    "H3": 36,
    "H4": 45,
    "H5": 53,
    "L1": 76,
    "L2": 91,
    "L3": 106,
    "L4": 120,
    "L5": 142,
    "W1": 1,
    "W2": 1,
}
NUM_REELS = 7
DEFAULT_SEED = 906_502_183
W2_ACTIVE_REELS = 4


def build_reel(seed: int, reel_index: int) -> list[str]:
    counts = COUNTS_PER_REEL.copy()
    if reel_index >= W2_ACTIVE_REELS:
        counts["W2"] = 0
        counts["H1"] += 1
    symbols = [
        symbol
        for symbol, count in counts.items()
        for _ in range(count)
    ]
    random.Random(seed + reel_index * 0x9E3779B1).shuffle(symbols)
    return symbols


def validate(reels: list[list[str]]) -> None:
    assert len(reels) == NUM_REELS
    assert len({len(reel) for reel in reels}) == 1
    for reel_index, reel in enumerate(reels):
        expected = Counter(COUNTS_PER_REEL)
        if reel_index >= W2_ACTIVE_REELS:
            expected["W2"] = 0
            expected["H1"] += 1
        assert Counter(reel) == expected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=lambda value: int(value, 0), default=DEFAULT_SEED)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "reels" / "BR0.csv",
    )
    args = parser.parse_args()

    reels = [build_reel(args.seed, reel_index) for reel_index in range(NUM_REELS)]
    validate(reels)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(zip(*reels))
    reel_hash = hashlib.sha256(args.output.read_bytes()).hexdigest()
    metadata_path = args.output.with_name("BR0.metadata.json")
    metadata_path.write_text(
        json.dumps(
            {
                "profile": "m2b_feature_adjusted",
                "seed": args.seed,
                "reelLength": len(reels[0]),
                "w2ActiveReels": W2_ACTIVE_REELS,
                "baseCountsPerReel": COUNTS_PER_REEL,
                "inactiveW2Replacement": "H1",
                "sha256": reel_hash,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"generated={args.output} reel_length={len(reels[0])} "
        f"seed={args.seed} sha256={reel_hash}"
    )


if __name__ == "__main__":
    main()
