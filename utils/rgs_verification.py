"""
Verify lookup-tale and book result format
Output statistics tested via RGS
"""

import json
import os
import warnings
import argparse
import importlib
from io import TextIOWrapper
import numpy as np
import zstandard as zst
import hashlib
import pickle
from math import floor
from utils.analysis.distribution_functions import (
    make_win_distribution,
    get_distribution_moments,
    get_distribution_average,
    non_zero_hitrate,
    prob_less_than_bet,
    get_prob_no_win,
    get_maxwin_hitrate,
    get_distribution_median,
    min_dist_difference,
    calculate_rtp,
    get_etl_cvar_p5k_10k_vales,
    conditional_value_at_risk,
    prob_win_at_least,
)
from src.write_data.write_data import get_sha_256

SUBMISSION_LIMITS = {
    "min_rtp": 0.960,
    "max_rtp": 0.967,
    "base_cost": 1.0,
    "max_cost": 50_000,
    "max_win": 1_000_000,
    "min_base_std": 0.6,
}

RISK_CHECKS = {
    "Top win": [("Top win", lambda s: s.max_win / 100, 100_000)],
    "Cost multiplier": [("Cost multiplier", lambda s: s.cost, 5_000)],
    "Volatility": [("Standard deviation", lambda s: s.std, 60)],
    "Worst 0.1% of rounds": [
        ("Relative to cost", lambda s: s.cvar, 700),
        ("Absolute", lambda s: s.cvar_abs, 50_000),
    ],
    "Tail liability": [
        ("RTP from 40x cost or more", lambda s: s.norm_etl40, 0.9),
        ("RTP from 10,000x or more", lambda s: s.norm_etl10k, 0.8),
        ("Both combined", lambda s: s.sum_etl, 1.5),
        ("Combined, in base bets", lambda s: s.sum_etl_abs, 10_000),
    ],
    "Big win frequency": [
        ("5,000x or more", lambda s: s.prob5k, 0.05),
        ("10,000x or more", lambda s: s.prob10k, 0.01),
        ("25,000x or more", lambda s: s.prob25k, 0.005),
        ("50,000x or more", lambda s: s.prob50k, 0.001),
        ("100,000x or more", lambda s: s.prob100k, 0.0005),
    ],
}

TEMPLATE_LIMITS = [
    (50e6, 500e3),
    (25e6, 500e3),
    (15e6, 250e3),
    (10e6, 100e3),
    (5e6, 50e3),
    (1e6, 10e3),
    (500e3, 10e3),
    (100e3, 10e3),
    (50e3, 1e3),
]
MAX_TEMPLATE_BET = 1_000  # Studio skips templates with a higher max base bet


class WinStatistics:
    """Statistics tested upon RGS upload"""

    def __init__(
        self,
        win_distribution=None,
        num_events=None,
        weight_range=None,
        min_win=None,
        max_win=None,
        min_diff=None,
        unique_wins=None,
        average_wins=None,
        cost=None,
        rtp=None,
        std=None,
        var=None,
        m2m=None,
        hr_max=None,
        non_zero_hr=None,
        prob_nil=None,
        prob_less_bet=None,
        num_non_zero_payouts=None,
        skew=None,
        excess_kurtosis=None,
        prob5k=None,
        prob10k=None,
        prob25k=None,
        prob50k=None,
        prob100k=None,
        etl40b=None,
        etl10k=None,
        norm_etl40=None,
        norm_etl10k=None,
        sum_etl=None,
        sum_etl_abs=None,
        cvar=None,
        cvar_abs=None,
    ):
        self.win_distribution = win_distribution
        self.num_events = num_events
        self.weight_range = weight_range
        self.min_win = min_win
        self.max_win = max_win
        self.min_diff = min_diff
        self.unique_wins = unique_wins
        self.average_win = average_wins
        self.cost = cost
        self.rtp = rtp
        self.std = std
        self.var = var
        self.m2m = m2m
        self.hr_max = hr_max
        self.non_zero_hr = non_zero_hr
        self.prob_nil = prob_nil
        self.num_non_zero_payouts = num_non_zero_payouts
        self.prob_less_bet = prob_less_bet
        self.skew = skew
        self.excess_kurtosis = excess_kurtosis
        self.prob5k = prob5k
        self.prob10k = prob10k
        self.prob25k = prob25k
        self.prob50k = prob50k
        self.prob100k = prob100k
        self.etl40b = etl40b
        self.etl10k = etl10k
        self.norm_etl40 = norm_etl40
        self.norm_etl10k = norm_etl10k
        self.sum_etl = sum_etl
        self.sum_etl_abs = sum_etl_abs
        self.cvar = cvar
        self.cvar_abs = cvar_abs

    def to_dict(self):
        map_object = {}
        for item in self.__dict__.keys():
            if item is not None:
                value = getattr(self, item)
                if isinstance(value, float):
                    # Keep 4 significant figures below 1 so small probabilities don't round to 0.
                    value = round(value, 3) if abs(value) >= 1 else float(f"{value:.4g}")
                map_object[item] = value
        return map_object


def verify_lookup_format(filename: str) -> list:
    "Duplicate RGS verification before upload."
    integer_payouts = []
    running_weight_total = 0
    min_win, max_win = None, None
    win_distribution = make_win_distribution(filename)

    with open(filename, "r", encoding="UTF-8") as f:
        for line in f:
            _, weight, payout = line.strip().split(",")
            weight = float(weight)
            payout = float(payout)

            # Payout checks
            assert payout.is_integer() and payout >= 0, "Payout mult be uint64 format:"
            if payout > 0:
                assert payout >= 10, "Minimum non-zero payout is 10 (RGS accepts 'cents' increments)."
            assert payout % 10 == 0, "Payout values must be in increments of 10."
            integer_payouts.append(int(payout))

            if weight > 0:
                if (min_win is None) or (payout < min_win):
                    min_win = payout
                if (max_win is None) or (payout > max_win):
                    max_win = payout
            # Weight checks
            assert weight.is_integer() and weight >= 0, "Weight must be uint64 format."
            running_weight_total += weight

    assert running_weight_total > 0, "Sum of weights must be > 0."
    assert running_weight_total <= np.iinfo(np.uint64).max, "Sum of weights must be <= MAX(uint64)"

    return win_distribution, integer_payouts, running_weight_total, min_win, max_win


# payout mult value match to lut + length match
def verify_books_and_payout_mults(books_filename: str) -> list:
    """Ensure the values written to the books match those in the lookup table exactly."""
    assert str(books_filename).endswith(".jsonl.zstd") or str(books_filename).endswith(
        "jsonl.zst"
    ), "Verification is only run for compressed book files of format .jsonl.zst."

    book_payout_ints = []
    total_num_events = 0
    with open(books_filename, "rb") as f:
        decompressor = zst.ZstdDecompressor()
        with decompressor.stream_reader(f) as reader:
            txt_stream = TextIOWrapper(reader, encoding="UTF-8")
            for line in txt_stream:
                line = line.strip()
                if not line:
                    continue

                try:
                    blob = json.loads(line)
                except json.JSONDecodeError:
                    raise RuntimeError("Invalid JSON format.")

                for key in ["payoutMultiplier", "id", "events"]:
                    if key not in blob:
                        raise RuntimeError(f"Missing required key: {key}")

                total_num_events += len(blob["events"])
                book_payout_ints.append(blob["payoutMultiplier"])

    return book_payout_ints, total_num_events


def compare_payout_values(book_int_payouts, lut_int_payouts) -> None:
    """Ensure payout multiplier values match between books and lookup tables."""
    book_ints = pickle.dumps(book_int_payouts)
    lut_ints = pickle.dumps(lut_int_payouts)
    assert hashlib.md5(book_ints).hexdigest() == hashlib.md5(lut_ints).hexdigest(), "Mismatch in payout array."


def get_num_non_zero_payouts(book_int_payouts) -> None:
    """Count non-zero payouts"""
    return len([p for p in book_int_payouts if p > 0])


def get_risk_failures(MathStats: object) -> dict:
    """Studio risk-check measures the mode is over, as {check: [(measure, value, limit), ...]}."""
    failures = {}
    for check, measures in RISK_CHECKS.items():
        for measure, get_value, limit in measures:
            value = get_value(MathStats)
            if np.float32(value) > np.float32(limit):
                failures.setdefault(check, []).append((measure, value, limit))
    return failures


def verify_mode_volatility(name: str, MathStats: object) -> dict:
    """Check a mode against Studio's risk checks. Returns the failures from get_risk_failures()."""
    failures = get_risk_failures(MathStats)

    if failures:
        warnings.warn(f"\nMode [{name}] fails Studio risk checks:\n")
        for check, measures in failures.items():
            for measure, value, limit in measures:
                print(f"\tVIOLATED: {check} - {measure}  VALUE: {round(value, 6):,.10g} --- LIMIT: {limit:,g}")
        print("\n\n")
    return failures


def verify_submission_limits(mode_stats: list) -> list:
    """Studio's submission checks. Returns one message per issue; Studio won't accept math with any issue."""
    limits = SUBMISSION_LIMITS
    issues = []
    for stats in mode_stats:
        # Studio rounds RTP to 4 decimal places (half away from zero) before checking it.
        rtp = floor(stats.rtp * 1e4 + 0.5) / 1e4
        if not limits["min_rtp"] <= rtp <= limits["max_rtp"]:
            issues.append(
                f"[{stats.name}] RTP is {stats.rtp:.2%}. It must be between "
                f"{limits['min_rtp']:.2%} and {limits['max_rtp']:.2%}."
            )
        if stats.cost > limits["max_cost"]:
            issues.append(
                f"[{stats.name}] Costs {stats.cost:,.10g}x. The most a mode can cost is {limits['max_cost']:,}x."
            )
        if stats.max_win / 100 > limits["max_win"]:
            issues.append(
                f"[{stats.name}] Top win is {stats.max_win / 100:,.10g}x. "
                f"The most any mode can pay is {limits['max_win']:,}x."
            )

    min_cost = min(stats.cost for stats in mode_stats)
    if min_cost != limits["base_cost"]:
        issues.append(
            f"[All modes] Your cheapest mode costs {min_cost:,.10g}x. One mode must be the 1x base game."
        )
    base_stds = [stats.std for stats in mode_stats if stats.cost == limits["base_cost"]]
    if base_stds and min(base_stds) < limits["min_base_std"]:
        issues.append(
            f"[All modes] Base game standard deviation is {min(base_stds):.2f}. "
            f"It must be at least {limits['min_base_std']:.2f}."
        )
    return issues


def get_max_base_bet(mode_stats: list, num_failed_checks: int) -> float:
    """Highest max base bet (USD) a bet template can have for this math. Studio gives the highest template at or
    below it; the template list itself is only in Studio."""
    if num_failed_checks >= len(TEMPLATE_LIMITS):
        return 0.0
    max_exposure, max_round_cost = TEMPLATE_LIMITS[num_failed_checks]
    top_win = max(stats.max_win / 100 for stats in mode_stats)
    top_cost = max(stats.cost for stats in mode_stats)

    max_bet = MAX_TEMPLATE_BET
    if top_win > 0:
        max_bet = min(max_bet, max_exposure / top_win)
    if top_cost > 0:
        max_bet = min(max_bet, max_round_cost / top_cost)
    return max_bet


def verify_studio_limits(mode_stats: list) -> None:
    """Print the game-wide results shown on the Studio math page: submission issues, risk checks and max bet."""
    issues = verify_submission_limits(mode_stats)
    failed_checks = [check for check in RISK_CHECKS if any(check in get_risk_failures(s) for s in mode_stats)]

    if issues:
        warnings.warn(f"\n\nStudio won't accept this math for submission. Issues to fix ({len(issues)}):\n")
        for issue in issues:
            print(f"\t{issue}")

    print(f"\nRisk checks: {len(RISK_CHECKS) - len(failed_checks)} of {len(RISK_CHECKS)} pass")
    if failed_checks:
        print(f"\tFailing (bet template limits lowered): {', '.join(failed_checks)}")
    print(
        f"Max base bet: up to ${get_max_base_bet(mode_stats, len(failed_checks)):,.2f}. "
        "Studio gives the highest bet template at or below this.\n"
    )


def get_lut_statistics(
    name, win_distribution, bet_cost, unique_payouts, weight_range, min_win, max_win, num_events
) -> object:
    """Run RGS statistic tests for upload verification."""

    var, std, skew, kurtosis = get_distribution_moments(win_distribution, bet_cost)
    total_weight = sum(list(win_distribution.values()))
    p5k, p10k, etl10k, etl40, cvarp01 = get_etl_cvar_p5k_10k_vales(win_distribution, bet_cost, total_weight)
    norm_etl40, norm_etl10k = etl40 / bet_cost, etl10k / bet_cost
    MathStats = WinStatistics(
        win_distribution=win_distribution,
        num_events=num_events,
        weight_range=weight_range,
        min_win=min_win,
        max_win=max_win,
        min_diff=min_dist_difference(win_distribution),
        unique_wins=unique_payouts,
        average_wins=float(get_distribution_average(win_distribution)),
        cost=bet_cost,
        rtp=calculate_rtp(win_distribution, bet_cost, weight_range),
        std=std / bet_cost,
        var=var,
        hr_max=get_maxwin_hitrate(win_distribution, weight_range),
        non_zero_hr=non_zero_hitrate(win_distribution, weight_range),
        prob_nil=get_prob_no_win(win_distribution, weight_range),
        prob_less_bet=prob_less_than_bet(win_distribution, bet_cost, weight_range),
        num_non_zero_payouts=get_num_non_zero_payouts(unique_payouts),
        skew=skew,
        excess_kurtosis=kurtosis,
        prob5k=p5k,
        prob10k=p10k,
        prob25k=prob_win_at_least(win_distribution, 25_000, total_weight),
        prob50k=prob_win_at_least(win_distribution, 50_000, total_weight),
        prob100k=prob_win_at_least(win_distribution, 100_000, total_weight),
        etl40b=etl40,
        etl10k=etl10k,
        norm_etl40=norm_etl40,
        norm_etl10k=norm_etl10k,
        sum_etl=norm_etl40 + norm_etl10k,
        sum_etl_abs=etl40 + etl10k,
        cvar=cvarp01,
        cvar_abs=conditional_value_at_risk(0.999, win_distribution, total_weight),
    )
    median = get_distribution_median(win_distribution, weight_range)

    if median > 0:
        m2m = MathStats.average_win / median
        MathStats.m2m = m2m
    else:
        MathStats.m2m = 0

    verify_mode_volatility(name, MathStats)
    return MathStats


def execute_all_tests(config, excluded_modes=[]):
    """Run all tests for a given game"""
    mode_stats = []
    for bet_mode in config.bet_modes:
        name = bet_mode.get_name()
        cost = bet_mode.get_cost()
        if name not in excluded_modes:
            book_name = f"books_{name}.jsonl.zst"
            lookup_name = f"lookUpTable_{name}_0.csv"
            book_file = os.path.join(config.publish_path, book_name)
            lut_file = os.path.join(config.publish_path, lookup_name)

            if not (os.path.exists(book_file)) or not (os.path.exists(lut_file)):
                raise RuntimeError("Books/Lookup file does not exist.")

            win_dist, lut_payouts, weights_range, min_win, max_win = verify_lookup_format(lut_file)
            # Fast path: use verification.json sidecar if available
            verification_file = os.path.join(
                os.path.join(config.library_path, "configs"), f"books_{name}.verification.json"
            )
            if os.path.exists(verification_file):
                print(f"[FAST PATH] Using verification sidecar for {name}")
                with open(verification_file, "r", encoding="UTF-8") as vf:
                    verification = json.load(vf)

                actual_hash = get_sha_256(book_file)
                assert (
                    actual_hash == verification["file_hash"]
                ), f"Book file SHA-256 mismatch for {name}! File may be corrupted."

                lut_payout_hash = hashlib.md5(pickle.dumps(lut_payouts)).hexdigest()
                assert (
                    lut_payout_hash == verification["payout_hash"]
                ), f"Payout hash mismatch for {name}! Book payouts != LUT payouts."

                assert verification["num_entries"] == len(
                    lut_payouts
                ), f"Entry count mismatch for {name}: sidecar={verification['num_entries']} vs LUT={len(lut_payouts)}"

                print(f"[FAST PATH] {name}: SHA-256 OK, payout hash OK, entries={verification['num_entries']}")
            else:
                print(f"[FALLBACK] No verification sidecar for {name}, reading books...")
                book_payouts, _ = verify_books_and_payout_mults(book_file)
                compare_payout_values(book_payouts, lut_payouts)

            num_events = len(lut_payouts)
            StatsObject = get_lut_statistics(
                name, win_dist, cost, lut_payouts, weights_range, min_win, max_win, num_events
            )
            setattr(StatsObject, "name", name)
            mode_stats.append(StatsObject)

    if mode_stats:
        verify_studio_limits(mode_stats)

    fname = f"games/{config.game_id}/library/stats_summary.json"
    write_all_stats(mode_stats, fname)


def write_all_stats(StatsList: object, filename: str) -> None:
    """Write all stats to JSON file."""
    all_stats = {}
    for Stats in StatsList:
        all_stats[Stats.name] = Stats.to_dict()
        # Don't print unique wins/distribution for brevity.
        del all_stats[Stats.name]["win_distribution"]
        del all_stats[Stats.name]["unique_wins"]

    with open(filename, "w", encoding="UTF-8") as f:
        f.write(json.dumps(all_stats, indent=4))


def load_game_config(game_id: str):
    """Load game config class"""
    module_path = f"games.{game_id}.game_config"
    module = importlib.import_module(module_path)
    config = getattr(module, "GameConfig")

    return config()


def main():
    """parse commandline arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", dest="games", nargs="+")
    arguments = parser.parse_args()
    for game_id in arguments.games:
        game_config = load_game_config(game_id)
        execute_all_tests(game_config)


if __name__ == "__main__":

    main()
