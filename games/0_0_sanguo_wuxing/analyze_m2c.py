#!/usr/bin/env python3
"""汇总 M2c base/bonus Books、成长等级和 RGS 验证信息。"""

from __future__ import annotations

import argparse
import io
import json
import math
from collections import Counter
from pathlib import Path

import zstandard


GAME_DIR = Path(__file__).resolve().parent
EVENT_TYPES = (
    "dualWildTriggerCandidate",
    "soulFreeSpinTrigger",
    "destinyWildCollected",
    "soulLevelUp",
    "soulWildPlaced",
    "soulWildConsumed",
    "soulFreeSpinSummary",
    "freeSpinEnd",
    "wincap",
)


def analyze_mode(mode: str, cost: float) -> dict:
    books_path = GAME_DIR / "library" / "publish_files" / f"books_{mode}.jsonl.zst"
    payouts = []
    base_wins = 0.0
    free_wins = 0.0
    components = Counter()
    events = Counter()
    final_levels = Counter()
    spins_awarded = Counter()
    total_collected = 0

    with books_path.open("rb") as handle:
        with zstandard.ZstdDecompressor().stream_reader(handle) as reader:
            for line in io.TextIOWrapper(reader, encoding="utf-8"):
                book = json.loads(line)
                payout = book["payoutMultiplier"] / 100
                payouts.append(payout)
                base_wins += book["baseGameWins"]
                free_wins += book["freeGameWins"]
                for event in book["events"]:
                    event_type = event["type"]
                    events[event_type] += 1
                    if event_type == "rtpComponentSummary":
                        for name, value in event["components"].items():
                            components[name] += value / 100
                    elif event_type == "soulFreeSpinSummary":
                        final_levels[event["finalLevel"]] += 1
                        spins_awarded[event["totalSpinsAwarded"]] += 1
                        total_collected += event["collectedW2"]

    count = len(payouts)
    mean_raw = sum(payouts) / count
    variance_raw = sum((value - mean_raw) ** 2 for value in payouts) / count
    standard_error_rtp = math.sqrt(variance_raw / count) / cost
    trigger_count = events["soulFreeSpinTrigger"]
    verification = json.loads(
        (
            GAME_DIR
            / "library"
            / "configs"
            / f"books_{mode}.verification.json"
        ).read_text(encoding="utf-8")
    )
    return {
        "simulationCount": count,
        "costX": cost,
        "rtp": mean_raw / cost,
        "rtp95ConfidenceInterval": [
            mean_raw / cost - 1.96 * standard_error_rtp,
            mean_raw / cost + 1.96 * standard_error_rtp,
        ],
        "baseGameRtp": base_wins / count / cost,
        "freeGameRtp": free_wins / count / cost,
        "hitRate": sum(value > 0 for value in payouts) / count,
        "averageRawPayoutX": mean_raw,
        "standardDeviationRawX": math.sqrt(variance_raw),
        "maximumObservedRawX": max(payouts),
        "wincapCount": sum(value >= 50_000 for value in payouts),
        "freegameTriggerCount": trigger_count,
        "freegameTriggerRate": trigger_count / count,
        "averageSpinsAwarded": (
            sum(spins * occurrences for spins, occurrences in spins_awarded.items())
            / trigger_count
            if trigger_count
            else 0
        ),
        "averageCollectedW2": total_collected / trigger_count if trigger_count else 0,
        "finalLevelDistribution": {
            str(level): occurrences for level, occurrences in sorted(final_levels.items())
        },
        "spinsAwardedDistribution": {
            str(spins): occurrences for spins, occurrences in sorted(spins_awarded.items())
        },
        "rtpComponents": {
            name: value / count / cost for name, value in sorted(components.items())
        },
        "eventCounts": {name: events[name] for name in EVENT_TYPES},
        "verification": verification,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="m2c")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = {
        "gameId": "0_0_sanguo_wuxing",
        "mathVersion": "m2c.0.0",
        "label": args.label,
        "reels": {
            reel: json.loads(
                (GAME_DIR / "reels" / f"{reel}.metadata.json").read_text(encoding="utf-8")
            )
            for reel in ("BR0", "FR0", "FRB0")
        },
        "modes": {
            "base": analyze_mode("base", 1.0),
            "bonus": analyze_mode("bonus", 100.0),
        },
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
