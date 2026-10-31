#!/usr/bin/env python3
"""M2d 多进程快速数学回归：保留 RNG/状态机，跳过 Book Event 序列化。"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from game_config import GameConfig
from gamestate import GameState
from src.state.run_sims import string_to_int


GAME_DIR = Path(__file__).resolve().parent
MODE_CRITERIA = {"base": "basegame", "bonus": "bonus"}
MODE_COST = {"base": 1.0, "bonus": 100.0}


def _no_event(*_args, **_kwargs):
    return None


def disable_custom_event_serialization() -> None:
    """替换项目模块中已直接导入的事件函数；事件函数本身不参与 RNG。"""
    import game_executables
    import gamestate

    for name in tuple(vars(game_executables)):
        if name.endswith("_event"):
            setattr(game_executables, name, _no_event)
    gamestate.enter_bonus_event = _no_event


class FastGameState(GameState):
    """与正式状态机等价，但不创建、复制或压缩 Book Event。"""

    def draw_board(self, emit_event=True, trigger_symbol="scatter"):
        return super().draw_board(emit_event=False, trigger_symbol=trigger_symbol)

    def record(self, description):
        return None

    def tumble_game_board(self):
        self.tumble_board()

    def emit_tumble_win_events(self):
        if self.win_data["totalWin"] > 0:
            self.evaluate_wincap()

    def evaluate_wincap(self):
        if (
            self.win_manager.running_bet_win >= self.config.wincap
            and not self.wincap_triggered
        ):
            self.wincap_triggered = True
            return True
        return False

    def set_end_tumble_event(self):
        return None

    def update_freespin(self):
        self.fs += 1
        self.win_manager.reset_spin_win()
        self.win_data = {}

    def end_freespin(self):
        return None

    def evaluate_finalwin(self):
        self.update_final_win()

    def imprint_wins(self):
        return None


def _new_accumulator(mode: str, start: int, stop: int) -> dict:
    return {
        "mode": mode,
        "start": start,
        "stop": stop,
        "count": 0,
        "sumPayout": 0.0,
        "sumPayoutSquared": 0.0,
        "sumBaseWin": 0.0,
        "sumFreeWin": 0.0,
        "hitCount": 0,
        "wincapCount": 0,
        "maximumPayout": 0.0,
        "triggerCount": 0,
        "sumSpinsAwarded": 0,
        "sumCollectedW2": 0,
        "finalLevels": Counter(),
        "payoutHistogramCents": Counter(),
        "components": Counter(),
    }


def run_shard(mode: str, start: int, stop: int) -> dict:
    disable_custom_event_serialization()
    config = GameConfig()
    state = FastGameState(config)
    state.betmode = mode
    state.criteria = MODE_CRITERIA[mode]
    seed_offset = string_to_int(state.criteria)
    result = _new_accumulator(mode, start, stop)

    for simulation in range(start, stop):
        state.run_spin(simulation, simulation_seed=seed_offset + simulation)
        payout = state.final_win
        payout_cents = int(round(payout * 100))
        result["count"] += 1
        result["sumPayout"] += payout
        result["sumPayoutSquared"] += payout * payout
        result["sumBaseWin"] += state.win_manager.basegame_wins
        result["sumFreeWin"] += state.win_manager.freegame_wins
        result["hitCount"] += payout > 0
        result["wincapCount"] += payout >= config.wincap
        result["maximumPayout"] = max(result["maximumPayout"], payout)
        result["payoutHistogramCents"][payout_cents] += 1
        for name, value in state.rtp_components.items():
            result["components"][name] += value

        triggered = mode == "bonus" or state.dual_wild_seen
        if triggered:
            result["triggerCount"] += 1
            result["sumSpinsAwarded"] += state.tot_fs
            result["sumCollectedW2"] += state.soul_total_collected
            result["finalLevels"][state.soul_level] += 1

    result["finalLevels"] = dict(result["finalLevels"])
    result["payoutHistogramCents"] = dict(result["payoutHistogramCents"])
    result["components"] = dict(result["components"])
    return result


def split_ranges(count: int, workers: int) -> list[tuple[int, int]]:
    shard_size, remainder = divmod(count, workers)
    ranges = []
    start = 0
    for worker in range(workers):
        stop = start + shard_size + (worker < remainder)
        ranges.append((start, stop))
        start = stop
    return ranges


def merge_shards(mode: str, shards: list[dict]) -> dict:
    total = _new_accumulator(mode, 0, sum(shard["count"] for shard in shards))
    for shard in sorted(shards, key=lambda item: item["start"]):
        for key in (
            "count",
            "sumPayout",
            "sumPayoutSquared",
            "sumBaseWin",
            "sumFreeWin",
            "hitCount",
            "wincapCount",
            "triggerCount",
            "sumSpinsAwarded",
            "sumCollectedW2",
        ):
            total[key] += shard[key]
        total["maximumPayout"] = max(total["maximumPayout"], shard["maximumPayout"])
        total["finalLevels"].update(shard["finalLevels"])
        total["payoutHistogramCents"].update(
            {int(key): value for key, value in shard["payoutHistogramCents"].items()}
        )
        total["components"].update(shard["components"])
    return total


def histogram_quantile(histogram: Counter, count: int, quantile: float) -> float:
    target = max(1, math.ceil(count * quantile))
    cumulative = 0
    for payout_cents, occurrences in sorted(histogram.items()):
        cumulative += occurrences
        if cumulative >= target:
            return payout_cents / 100
    raise RuntimeError("空 payout histogram")


def summarize(total: dict) -> dict:
    mode = total["mode"]
    count = total["count"]
    cost = MODE_COST[mode]
    mean = total["sumPayout"] / count
    variance = max(0.0, total["sumPayoutSquared"] / count - mean * mean)
    rtp_standard_error = math.sqrt(variance / count) / cost
    trigger_count = total["triggerCount"]
    histogram = total["payoutHistogramCents"]
    return {
        "simulationCount": count,
        "costX": cost,
        "rtp": mean / cost,
        "rtpStandardError": rtp_standard_error,
        "rtp95ConfidenceInterval": [
            mean / cost - 1.96 * rtp_standard_error,
            mean / cost + 1.96 * rtp_standard_error,
        ],
        "baseGameRtp": total["sumBaseWin"] / count / cost,
        "freeGameRtp": total["sumFreeWin"] / count / cost,
        "hitRate": total["hitCount"] / count,
        "averageRawPayoutX": mean,
        "standardDeviationRawX": math.sqrt(variance),
        "maximumObservedRawX": total["maximumPayout"],
        "wincapCount": total["wincapCount"],
        "triggerCount": trigger_count,
        "triggerRate": trigger_count / count,
        "averageSpinsAwarded": (
            total["sumSpinsAwarded"] / trigger_count if trigger_count else 0
        ),
        "averageCollectedW2": (
            total["sumCollectedW2"] / trigger_count if trigger_count else 0
        ),
        "finalLevelDistribution": {
            str(level): occurrences
            for level, occurrences in sorted(total["finalLevels"].items())
        },
        "payoutQuantilesRawX": {
            str(quantile): histogram_quantile(histogram, count, quantile)
            for quantile in (0.5, 0.9, 0.99, 0.999, 0.9999)
        },
        "rtpComponents": {
            name: value / count / cost
            for name, value in sorted(total["components"].items())
        },
    }


def reel_metadata() -> dict:
    return {
        reel: json.loads(
            (GAME_DIR / "reels" / f"{reel}.metadata.json").read_text(encoding="utf-8")
        )
        for reel in ("BR0", "FR0", "FRB0")
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sims", type=int, default=1_000_000)
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--modes", default="base,bonus")
    parser.add_argument(
        "--output",
        type=Path,
        default=GAME_DIR / "validation" / "m2d_fast_regression.json",
    )
    args = parser.parse_args()
    if args.sims <= 0:
        raise ValueError("--sims 必须大于 0")
    if not 1 <= args.workers <= 8:
        raise ValueError("--workers 必须在 1–8 之间")
    modes = [mode.strip() for mode in args.modes.split(",") if mode.strip()]
    if not modes or set(modes) - set(MODE_CRITERIA):
        raise ValueError("--modes 只支持 base,bonus")

    started = time.time()
    output = {
        "gameId": "0_0_sanguo_wuxing",
        "mathVersion": GameConfig().math_version,
        "method": "eventless-exact-state-machine-v1",
        "seedContract": "string_to_int(criteria)+simulation_index",
        "workers": args.workers,
        "reels": reel_metadata(),
        "modes": {},
    }

    for mode in modes:
        shards = []
        ranges = split_ranges(args.sims, args.workers)
        mode_started = time.time()
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(run_shard, mode, start, stop): (start, stop)
                for start, stop in ranges
            }
            for future in as_completed(futures):
                shard = future.result()
                shards.append(shard)
                print(
                    f"{mode} shard {shard['start']}:{shard['stop']} "
                    f"rawMean={shard['sumPayout']/shard['count']:.6f}",
                    flush=True,
                )
        output["modes"][mode] = summarize(merge_shards(mode, shards))
        output["modes"][mode]["elapsedSeconds"] = time.time() - mode_started
        print(
            f"{mode} rtp={output['modes'][mode]['rtp']:.8f} "
            f"ci95={output['modes'][mode]['rtp95ConfidenceInterval']}",
            flush=True,
        )

    output["elapsedSeconds"] = time.time() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote={args.output} elapsed={output['elapsedSeconds']:.2f}s")


if __name__ == "__main__":
    main()
