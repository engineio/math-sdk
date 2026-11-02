#!/usr/bin/env python3
"""使用 Stake Engine 游戏状态快速搜索 M2a reel 候选。

该工具不写 books/LUT，只比较符号计数指数和确定性排列种子。最终候选仍必须由
run.py 运行至少 100,000 局并通过 RGS 哈希校验。
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

from game_config import GameConfig
from gamestate import GameState


BASE_WEIGHTS = {
    "H1": 2.0,
    "H2": 3.0,
    "H3": 4.0,
    "H4": 5.0,
    "H5": 6.0,
    "L1": 9.0,
    "L2": 11.0,
    "L3": 13.0,
    "L4": 15.0,
    "L5": 18.0,
}
WILD_COUNTS = {"W1": 1, "W2": 1}
PAYING_STOPS_PER_REEL = 717
NUM_REELS = 7
DEFAULT_BASE_SEED = 0x36072026


def counts_for_exponent(exponent: float) -> dict[str, int]:
    transformed = {symbol: weight**exponent for symbol, weight in BASE_WEIGHTS.items()}
    total = sum(transformed.values())
    exact = {
        symbol: value / total * PAYING_STOPS_PER_REEL
        for symbol, value in transformed.items()
    }
    counts = {symbol: math.floor(value) for symbol, value in exact.items()}
    remaining = PAYING_STOPS_PER_REEL - sum(counts.values())
    for symbol in sorted(exact, key=lambda name: (-(exact[name] - counts[name]), name))[:remaining]:
        counts[symbol] += 1
    return counts | WILD_COUNTS


def build_reels(counts: dict[str, int], seed: int) -> list[list[str]]:
    reels = []
    for reel_index in range(NUM_REELS):
        symbols = [
            symbol
            for symbol, count in counts.items()
            for _ in range(count)
        ]
        random.Random(seed + reel_index * 0x9E3779B1).shuffle(symbols)
        reels.append(symbols)
    return reels


def evaluate_candidate(reels: list[list[str]], spins: int, seed: int) -> dict:
    config = GameConfig()
    config.reels["BR0"] = reels
    state = GameState(config)
    state.betmode = "base"
    state.criteria = "basegame"

    payout_total = 0.0
    hits = 0
    dual_wild_candidates = 0
    maximum_win = 0.0

    for spin in range(spins):
        state.run_spin(spin, simulation_seed=seed + spin)
        payout = state.final_win
        payout_total += payout
        hits += payout > 0
        dual_wild_candidates += state.dual_wild_seen
        maximum_win = max(maximum_win, payout)
        state.library.clear()
        state._payout_ints.clear()

    return {
        "spins": spins,
        "rtp": payout_total / spins,
        "hit_rate": hits / spins,
        "dual_wild_rate": dual_wild_candidates / spins,
        "max_win_x": maximum_win,
    }


def score(result: dict, target_rtp: float) -> float:
    hit_penalty = max(0.0, 0.30 - result["hit_rate"]) + max(0.0, result["hit_rate"] - 0.45)
    trigger_min = 1 / 260
    trigger_max = 1 / 180
    trigger_penalty = max(0.0, trigger_min - result["dual_wild_rate"])
    trigger_penalty += max(0.0, result["dual_wild_rate"] - trigger_max)
    return abs(result["rtp"] - target_rtp) + hit_penalty * 3 + trigger_penalty * 10


def write_reels(path: Path, reels: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        csv.writer(handle).writerows(zip(*reels))


def parse_exponents(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spins", type=int, default=5_000)
    parser.add_argument("--target-rtp", type=float, default=0.485)
    parser.add_argument("--exponents", type=parse_exponents, default=parse_exponents("0.84,0.85,0.86,0.87,0.88"))
    parser.add_argument("--seed-count", type=int, default=3)
    parser.add_argument("--base-seed", type=lambda value: int(value, 0), default=DEFAULT_BASE_SEED)
    parser.add_argument("--apply-best", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "reels" / "BR0.csv",
    )
    args = parser.parse_args()

    if args.spins <= 0 or args.seed_count <= 0:
        raise ValueError("--spins 和 --seed-count 必须大于 0")

    candidates = []
    for exponent in args.exponents:
        counts = counts_for_exponent(exponent)
        for seed_index in range(args.seed_count):
            seed = args.base_seed + seed_index * 0x10001
            reels = build_reels(counts, seed)
            result = evaluate_candidate(reels, args.spins, seed ^ 0xA5A5A5A5)
            candidate = {
                "exponent": exponent,
                "seed": seed,
                "counts": counts,
                **result,
            }
            candidate["score"] = score(candidate, args.target_rtp)
            candidates.append(candidate)
            print(json.dumps(candidate, ensure_ascii=False, sort_keys=True))

    candidates.sort(key=lambda candidate: (candidate["score"], candidate["exponent"], candidate["seed"]))
    best = candidates[0]
    print("BEST=" + json.dumps(best, ensure_ascii=False, sort_keys=True))

    if args.apply_best:
        write_reels(args.output, build_reels(best["counts"], best["seed"]))
        metadata_path = args.output.with_name("BR0.metadata.json")
        metadata_path.write_text(
            json.dumps(
                {
                    "profile": "m2a_flattened",
                    "searchSpins": args.spins,
                    "targetRtp": args.target_rtp,
                    **best,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"APPLIED={args.output}")


if __name__ == "__main__":
    main()
