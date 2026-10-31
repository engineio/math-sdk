#!/usr/bin/env python3
"""汇总 M2b 压缩 books 中的 RTP、功能和触发分项。"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import zstandard


GAME_DIR = Path(__file__).resolve().parent


def analyze(books_path: Path) -> dict:
    payouts = []
    components = Counter()
    feature_counts = Counter()
    charge_counts = Counter()
    event_counts = Counter()

    with books_path.open("rb") as handle:
        with zstandard.ZstdDecompressor().stream_reader(handle) as reader:
            for line in reader.read().decode("utf-8").splitlines():
                book = json.loads(line)
                payouts.append(book["payoutMultiplier"] / 100)
                for event in book["events"]:
                    event_counts[event["type"]] += 1
                    if event["type"] != "rtpComponentSummary":
                        continue
                    for name, value in event["components"].items():
                        components[name] += value / 100
                    feature_counts[len(event["executedFeatures"])] += 1
                    charge_counts[event["charge"]] += 1

    spins = len(payouts)
    total_payout = sum(payouts)
    hit_count = sum(payout > 0 for payout in payouts)
    mean = total_payout / spins
    variance = sum((payout - mean) ** 2 for payout in payouts) / spins
    dual_wild_count = event_counts["dualWildTriggerCandidate"]

    return {
        "gameId": "0_0_sanguo_wuxing",
        "mathVersion": "m2b.0.0",
        "simulationCount": spins,
        "metrics": {
            "baseGameRtp": mean,
            "hitRate": hit_count / spins,
            "averageWinPerHit": total_payout / hit_count if hit_count else 0.0,
            "standardDeviation": math.sqrt(variance),
            "maximumObservedWinX": max(payouts),
            "dualWildCandidateCount": dual_wild_count,
            "dualWildCandidateRate": dual_wild_count / spins,
            "dualWildCandidateOdds": spins / dual_wild_count if dual_wild_count else None,
        },
        "rtpComponents": {
            name: value / spins for name, value in sorted(components.items())
        },
        "executedFeatureCountDistribution": {
            str(count): occurrences
            for count, occurrences in sorted(feature_counts.items())
        },
        "chargeDistribution": {
            str(charge): occurrences
            for charge, occurrences in sorted(charge_counts.items())
        },
        "eventCounts": {
            event: event_counts[event]
            for event in (
                "megaSymbolsDetected",
                "rescueApplied",
                "returnSymbolMarked",
                "returnWildsApplied",
                "featureQueued",
                "featureApplied",
                "roundMultiplierApplied",
                "dualWildTriggerCandidate",
            )
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--books",
        type=Path,
        default=GAME_DIR / "library" / "publish_files" / "books_base.jsonl.zst",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = analyze(args.books)
    result["reel"] = json.loads(
        (GAME_DIR / "reels" / "BR0.metadata.json").read_text(encoding="utf-8")
    )
    result["verification"] = json.loads(
        (GAME_DIR / "library" / "configs" / "books_base.verification.json").read_text(
            encoding="utf-8"
        )
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
