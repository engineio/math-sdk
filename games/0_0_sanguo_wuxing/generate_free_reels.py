#!/usr/bin/env python3
"""生成 M2c 自然免费游戏与 Bonus Buy 的确定性 reel strips。"""

import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path


GAME_DIR = Path(__file__).resolve().parent
NUM_REELS = 7
BASE_COUNTS = {
    "H1": 20,
    "H2": 28,
    "H3": 36,
    "H4": 45,
    "H5": 53,
    "L1": 76,
    "L2": 91,
    "L3": 106,
    "L4": 120,
}
PROFILES = {
    "FR0": {
        "seed": 0x360C2026,
        "counts": {
            **{symbol: count * 10 for symbol, count in BASE_COUNTS.items()},
            "L5": 1359,
            "W1": 0,
            "W2": 81,
        },
        "w2CountsPerReel": [82, 82, 81, 81, 81, 81, 81],
        "purpose": "natural_freegame",
    },
    "FRB0": {
        "seed": 0x360C100,
        "counts": {
            **{symbol: count * 10 for symbol, count in BASE_COUNTS.items()},
            "L5": 1358,
            "W1": 0,
            "W2": 82,
        },
        "w2CountsPerReel": [83, 83, 83, 82, 82, 82, 82],
        "purpose": "bonus_buy_100x",
    },
}


def build_reels(
    seed: int,
    counts: dict[str, int],
    w2_counts_per_reel: list[int] | None = None,
) -> list[list[str]]:
    reels = []
    for reel_index in range(NUM_REELS):
        reel_counts = counts.copy()
        if w2_counts_per_reel:
            w2_count = w2_counts_per_reel[reel_index]
            reel_counts["L5"] += reel_counts["W2"] - w2_count
            reel_counts["W2"] = w2_count
        symbols = [
            symbol
            for symbol, count in reel_counts.items()
            for _ in range(count)
        ]
        random.Random(seed + reel_index * 0x9E3779B1).shuffle(symbols)
        reels.append(symbols)
    return reels


def write_profile(name: str, profile: dict) -> None:
    reels = build_reels(
        profile["seed"],
        profile["counts"],
        profile.get("w2CountsPerReel"),
    )
    assert len({len(reel) for reel in reels}) == 1
    expected_counts = []
    for reel_index in range(NUM_REELS):
        expected = profile["counts"].copy()
        if profile.get("w2CountsPerReel"):
            w2_count = profile["w2CountsPerReel"][reel_index]
            expected["L5"] += expected["W2"] - w2_count
            expected["W2"] = w2_count
        expected_counts.append(expected)
    assert all(
        Counter(reel) == Counter(expected_counts[index])
        for index, reel in enumerate(reels)
    )

    output = GAME_DIR / "reels" / f"{name}.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(zip(*reels))

    reel_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    metadata = {
        "profile": f"m2d_{profile['purpose']}",
        "seed": profile["seed"],
        "reelLength": len(reels[0]),
        "countsPerReel": expected_counts,
        "sha256": reel_hash,
    }
    output.with_name(f"{name}.metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"generated={output} reel_length={len(reels[0])} sha256={reel_hash}")


if __name__ == "__main__":
    for profile_name, profile_data in PROFILES.items():
        write_profile(profile_name, profile_data)
