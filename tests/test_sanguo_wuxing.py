"""《三国五行传》M2c 项目测试。"""

import importlib
import hashlib
import itertools
import json
import random
import sys
from pathlib import Path

import pytest


GAME_DIR = Path(__file__).resolve().parents[1] / "games" / "0_0_sanguo_wuxing"
sys.path.insert(0, str(GAME_DIR))

game_config = importlib.import_module("game_config")
game_calculations = importlib.import_module("game_calculations")
gamestate = importlib.import_module("gamestate")


@pytest.fixture
def state():
    config = game_config.GameConfig()
    result = gamestate.GameState(config)
    result.betmode = "base"
    result.criteria = "basegame"
    result.gametype = config.basegame_type
    return result


def test_configuration_is_7_by_7_and_capped(state):
    assert state.config.math_version == "m2d.0.0-candidate"
    assert state.config.stream_books
    assert not state.config.write_event_list
    assert state.config.num_reels == 7
    assert state.config.num_rows == [7] * 7
    assert state.config.wincap == 50_000
    assert state.config.paytable[(5, "H1")] == 10.0
    assert state.config.paytable[(49, "L5")] == 20.0
    assert {mode.get_name() for mode in state.config.bet_modes} == {"base", "bonus"}


def test_wild_candidate_selection_uses_single_owner():
    Candidate = game_calculations.ClusterCandidate
    shared = frozenset({(1, 1)})
    low = Candidate("L5", frozenset({(1, 1), (1, 2), (1, 3), (1, 4), (1, 5)}), shared, 0.4)
    high = Candidate("H1", frozenset({(1, 1), (2, 1), (3, 1), (4, 1), (5, 1)}), shared, 10.0)
    selected = game_calculations.GameCalculations._select_clusters([high, low])
    assert selected == [high]


def test_bitmask_wild_selection_matches_exhaustive_optimum():
    Candidate = game_calculations.ClusterCandidate
    rng = random.Random(0x360C)
    for case in range(50):
        candidates = []
        for index in range(8):
            wilds = frozenset(
                position
                for position in ((0, 0), (1, 1), (2, 2), (3, 3))
                if rng.random() < 0.4
            )
            candidates.append(
                Candidate(
                    symbol=f"S{index}",
                    positions=frozenset({(index, 0)}).union(wilds),
                    wild_positions=wilds,
                    payout=float(rng.randrange(1, 30)),
                )
            )

        selected = game_calculations.GameCalculations._select_clusters(candidates)
        selected_total = sum(candidate.payout for candidate in selected)
        legal_totals = []
        for size in range(len(candidates) + 1):
            for subset in itertools.combinations(candidates, size):
                all_wilds = [
                    position
                    for candidate in subset
                    for position in candidate.wild_positions
                ]
                if len(all_wilds) == len(set(all_wilds)):
                    legal_totals.append(sum(candidate.payout for candidate in subset))
        assert selected_total == max(legal_totals), f"case={case}"


def test_reel_counts_match_manifest(state):
    expected = {
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
    for reel_index, reel in enumerate(state.config.reels["BR0"]):
        reel_expected = expected.copy()
        if reel_index >= 4:
            reel_expected["W2"] = 0
            reel_expected["H1"] += 1
        assert {symbol: reel.count(symbol) for symbol in reel_expected} == reel_expected


def test_m2a_reel_hash_and_validation_snapshot():
    reel_path = GAME_DIR / "reels" / "archive" / "BR0_m2a.csv"
    reel_hash = hashlib.sha256(reel_path.read_bytes()).hexdigest()
    validation = json.loads(
        (GAME_DIR / "validation" / "m2a_100k_summary.json").read_text(encoding="utf-8")
    )
    assert reel_hash == validation["reelSha256"]
    assert 0.48 <= validation["metrics"]["naturalRtp"] <= 0.49
    assert 0.30 <= validation["metrics"]["hitRate"] <= 0.45
    assert 1 / 260 <= validation["metrics"]["dualWildCandidateRate"] <= 1 / 180


def test_m2b_reel_hash_and_validation_snapshot():
    reel_path = GAME_DIR / "reels" / "BR0.csv"
    reel_hash = hashlib.sha256(reel_path.read_bytes()).hexdigest()
    validation = json.loads(
        (GAME_DIR / "validation" / "m2b_100k_summary.json").read_text(encoding="utf-8")
    )
    assert reel_hash == validation["reel"]["sha256"]
    assert 0.65 <= validation["metrics"]["baseGameRtp"] <= 0.70
    assert 0.30 <= validation["metrics"]["hitRate"] <= 0.45
    assert 1 / 260 <= validation["metrics"]["dualWildCandidateRate"] <= 1 / 180
    assert validation["verification"]["num_entries"] == 100_000


def test_m2d_free_reels_and_million_spin_snapshot():
    expected_w2 = {
        "FR0": [82, 82, 81, 81, 81, 81, 81],
        "FRB0": [83, 83, 83, 82, 82, 82, 82],
    }
    for reel_name, counts in expected_w2.items():
        reel_path = GAME_DIR / "reels" / f"{reel_name}.csv"
        metadata = json.loads(
            (GAME_DIR / "reels" / f"{reel_name}.metadata.json").read_text(encoding="utf-8")
        )
        assert hashlib.sha256(reel_path.read_bytes()).hexdigest() == metadata["sha256"]
        assert [item["W2"] for item in metadata["countsPerReel"]] == counts

    validation = json.loads(
        (GAME_DIR / "validation" / "m2d_fast_1m_candidate.json").read_text(encoding="utf-8")
    )
    assert validation["mathVersion"] == "m2d.0.0-candidate"
    assert 0.90 <= validation["modes"]["base"]["rtp"] <= 1.00
    assert validation["modes"]["base"]["triggerCount"] == 4_488
    assert 0.93 <= validation["modes"]["bonus"]["rtp"] <= 0.98
    assert validation["modes"]["bonus"]["finalLevelDistribution"]["7"] > 2_000
    assert validation["modes"]["base"]["simulationCount"] == 1_000_000
    assert validation["modes"]["bonus"]["simulationCount"] == 1_000_000


def test_fixed_seed_round_is_reproducible(state):
    state.run_spin(360, simulation_seed=0x36072026)
    first = state.library[361]

    second_state = gamestate.GameState(state.config)
    second_state.betmode = "base"
    second_state.criteria = "basegame"
    second_state.run_spin(360, simulation_seed=0x36072026)
    assert first == second_state.library[361]


def test_mega_detection_marks_non_overlapping_2x2(state, monkeypatch):
    monkeypatch.setattr(state.config, "mega_merge_probability", 1.0)
    state.draw_board(emit_event=False)
    for reel, row in ((0, 0), (1, 0), (0, 1), (1, 1)):
        state.board[reel][row] = state.create_symbol("L5")
    state.prepare_mega_groups()
    assert any(
        group["positions"] == frozenset({(0, 0), (1, 0), (0, 1), (1, 1)})
        for group in state.mega_groups
    )


def test_rescue_places_configured_wild_count(state, monkeypatch):
    monkeypatch.setattr(state.config, "rescue_trigger_probability", 1.0)
    monkeypatch.setattr(state.config, "rescue_wild_count_weights", {2: 1})
    state.draw_board(emit_event=False)
    before = state.count_symbols_on_board("W1")
    assert state.attempt_rescue()
    assert state.count_symbols_on_board("W1") == before + 2
    assert state.book.events[-1]["type"] == "rescueApplied"


def test_return_leaves_two_wilds_after_cluster(state):
    state.draw_board(emit_event=False)
    state.return_mark_symbol = "L5"
    positions = [(0, row) for row in range(5)]
    for reel, row in positions:
        state.board[reel][row] = state.create_symbol("L5")
    state.win_data = {
        "totalWin": 0.4,
        "wins": [
            {
                "symbol": "L5",
                "clusterSize": 5,
                "win": 0.4,
                "positions": [{"reel": reel, "row": row} for reel, row in positions],
                "meta": {"globalMult": 1, "clusterMult": 1},
            }
        ],
    }
    state.prepare_return_wilds()
    assert state.apply_pending_return_wilds()
    assert state.count_symbols_on_board("W1") >= 2
    assert state.book.events[-1]["type"] == "returnWildsApplied"


def test_six_charges_queue_all_five_features(state):
    for _ in range(6):
        state.charge_feature_meter()
    assert state.feature_queue == ["wood", "fire", "metal", "water", "earth"]


def test_two_features_apply_2x_round_multiplier(state):
    state.executed_features = ["wood", "fire"]
    state.win_manager.update_spinwin(10.0)
    state.apply_round_feature_multiplier()
    assert state.win_manager.running_bet_win == 20.0
    assert state.rtp_components["roundMultiplier"] == 10.0
    assert state.book.events[-1]["multiplier"] == 2


def test_full_board_soul_overlay_has_one_owner_and_one_multiplier(state):
    state.draw_board(emit_event=False)
    for reel in range(7):
        for row in range(7):
            state.board[reel][row] = state.create_symbol("L5")
    state.board[0][0] = state.create_symbol("H1")
    state.soul_positions = {(reel, row) for reel in range(7) for row in range(7)}
    state.soul_multiplier = 10
    state.current_win_source = "freeNatural"

    _, result = state.evaluate_sanguo_clusters()

    assert result["totalWin"] == 3000.0
    assert len(result["wins"]) == 1
    assert result["wins"][0]["symbol"] == "H1"
    assert result["wins"][0]["meta"]["soulMultiplier"] == 10
    assert state.soul_consumed
    assert state.rtp_components["soulMultiplier"] == 2700.0


def test_five_new_destiny_wilds_upgrade_level_and_add_spins(state):
    state.initialize_soul_freegame("test")
    state.collect_destiny_wilds([(0, row) for row in range(5)])

    assert state.soul_level == 2
    assert state.soul_level_progress == 0
    assert state.tot_fs == 9
    assert state.soul_multiplier == 1
    assert len(state.soul_positions) == 4
    assert [event["type"] for event in state.book.events[-3:]] == [
        "destinyWildCollected",
        "soulLevelUp",
        "soulWildPlaced",
    ]


def test_bonus_buy_runs_formal_soul_freegame(state):
    state.betmode = "bonus"
    state.criteria = "bonus"
    state.run_spin(12, simulation_seed=0x360C100)
    book = state.library[13]
    event_types = [event["type"] for event in book["events"]]

    assert event_types[0] == "enterBonus"
    assert "soulFreeSpinTrigger" in event_types
    assert "soulWildPlaced" in event_types
    assert "soulFreeSpinSummary" in event_types
    assert "freeSpinEnd" in event_types
    assert book["baseGameWins"] == 0
    assert book["freeGameWins"] == book["payoutMultiplier"] / 100


def test_m2d_full_book_event_contract_snapshots():
    for mode in ("base", "bonus"):
        snapshot = json.loads(
            (
                GAME_DIR
                / "validation"
                / f"m2d_event_contract_{mode}_10k.json"
            ).read_text(encoding="utf-8")
        )
        verification = json.loads(
            (
                GAME_DIR
                / "library"
                / "configs"
                / f"books_{mode}.verification.json"
            ).read_text(encoding="utf-8")
        )
        assert snapshot["status"] == "passed"
        assert snapshot["bookCount"] == 10_000
        assert snapshot["eventCounts"]["finalWin"] == 10_000
        assert verification["num_entries"] == 10_000
