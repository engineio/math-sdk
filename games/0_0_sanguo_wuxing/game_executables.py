"""游戏专用组合动作。"""

import random

from game_calculations import GameCalculations
from game_events import (
    dual_wild_trigger_candidate_event,
    feature_applied_event,
    feature_queued_event,
    mega_symbols_detected_event,
    rescue_applied_event,
    return_symbol_marked_event,
    return_wilds_applied_event,
    round_multiplier_applied_event,
    rtp_component_summary_event,
    destiny_wild_collected_event,
    soul_freespin_summary_event,
    soul_freespin_trigger_event,
    soul_level_up_event,
    soul_wild_consumed_event,
    soul_wild_placed_event,
)
from src.calculations.cluster import Cluster
from src.calculations.statistics import get_random_outcome


class GameExecutables(GameCalculations):
    def get_clusters_update_wins(self):
        self.board, self.win_data = self.evaluate_sanguo_clusters()
        Cluster.record_cluster_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        self.win_manager.tumble_win = self.win_data["totalWin"]

    def check_dual_wild_trigger_candidate(self):
        if self.gametype != self.config.basegame_type or self.dual_wild_seen:
            return False

        w1_positions = []
        w2_positions = []
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                symbol = self.board[reel][row].name
                if symbol == "W1":
                    w1_positions.append((reel, row))
                elif symbol == "W2":
                    w2_positions.append((reel, row))

        if w1_positions and w2_positions:
            self.dual_wild_seen = True
            self.dual_wild_w1_positions = w1_positions
            self.dual_wild_w2_positions = w2_positions
            dual_wild_trigger_candidate_event(self, w1_positions, w2_positions)
            self.record(
                {
                    "kind": "dualWildCandidate",
                    "symbol": "W1+W2",
                    "gametype": self.gametype,
                }
            )
            return True
        return False

    @staticmethod
    def _json_positions(positions):
        return [{"reel": reel, "row": row + 1} for reel, row in sorted(positions)]

    def _ordinary_positions(self):
        return [
            (reel, row)
            for reel in range(self.config.num_reels)
            for row in range(self.config.num_rows[reel])
            if self.board[reel][row].name in self.config.symbol_rank
        ]

    def _draw_ordinary_symbol_name(self):
        while True:
            reel = random.choice(self.reelstrip)
            symbol = random.choice(reel)
            if symbol in self.config.symbol_rank:
                return symbol

    def prepare_mega_groups(self):
        """识别本稳定盘面的非重叠 2×2 超大符号覆盖层。"""
        groups = []
        occupied = set()
        for reel in range(self.config.num_reels - 1):
            for row in range(self.config.num_rows[reel] - 1):
                positions = frozenset(
                    {
                        (reel, row),
                        (reel + 1, row),
                        (reel, row + 1),
                        (reel + 1, row + 1),
                    }
                )
                names = {self.board[col][row_].name for col, row_ in positions}
                if len(names) != 1:
                    continue
                symbol = next(iter(names))
                if symbol not in self.config.symbol_rank or positions.intersection(occupied):
                    continue
                if random.random() <= self.config.mega_merge_probability:
                    groups.append({"symbol": symbol, "positions": positions})
                    occupied.update(positions)

        self.mega_groups = groups
        if groups:
            mega_symbols_detected_event(self, groups)
            self.record(
                {
                    "kind": "megaDetected",
                    "symbol": "+".join(sorted({group["symbol"] for group in groups})),
                    "gametype": self.gametype,
                }
            )

    def activate_return_mark(self):
        if random.random() > self.config.return_mark_probability:
            return False
        low_symbols = sorted(
            {
                self.board[reel][row].name
                for reel in range(self.config.num_reels)
                for row in range(self.config.num_rows[reel])
                if self.board[reel][row].name.startswith("L")
            }
        )
        if not low_symbols:
            return False
        self.return_mark_symbol = random.choice(low_symbols)
        return_symbol_marked_event(self, self.return_mark_symbol)
        self.record(
            {
                "kind": "returnMarked",
                "symbol": self.return_mark_symbol,
                "gametype": self.gametype,
            }
        )
        return True

    def attempt_rescue(self):
        if random.random() > self.config.rescue_trigger_probability:
            return False
        eligible = self._ordinary_positions()
        if not eligible:
            return False
        requested = get_random_outcome(self.config.rescue_wild_count_weights)
        positions = sorted(random.sample(eligible, min(requested, len(eligible))))
        for reel, row in positions:
            self.board[reel][row] = self.create_symbol("W1")
        self.get_special_symbols_on_board()
        rescue_applied_event(self, positions)
        self.record(
            {
                "kind": "rescue",
                "symbol": "W1",
                "count": len(positions),
                "gametype": self.gametype,
            }
        )
        return True

    def prepare_return_wilds(self):
        self.pending_return_clusters = []
        if not self.return_mark_symbol:
            return
        for win in self.win_data["wins"]:
            if win["symbol"] == self.return_mark_symbol:
                positions = [(position["reel"], position["row"]) for position in win["positions"]]
                self.pending_return_clusters.append(positions)

    def apply_pending_return_wilds(self):
        if not self.pending_return_clusters:
            return False
        chosen = []
        used = set()
        for cluster_positions in self.pending_return_clusters:
            legal = [
                position
                for position in cluster_positions
                if position not in used
                and self.board[position[0]][position[1]].name in self.config.symbol_rank
            ]
            if len(legal) < self.config.return_wilds_per_cluster:
                legal.extend(
                    position
                    for position in self._ordinary_positions()
                    if position not in used and position not in legal
                )
            count = min(self.config.return_wilds_per_cluster, len(legal))
            selected = random.sample(legal, count)
            for position in selected:
                used.add(position)
                chosen.append(position)

        for reel, row in chosen:
            self.board[reel][row] = self.create_symbol("W1")
        self.pending_return_clusters = []
        if not chosen:
            return False
        self.get_special_symbols_on_board()
        return_wilds_applied_event(self, self.return_mark_symbol, sorted(chosen))
        self.record(
            {
                "kind": "returnWilds",
                "symbol": self.return_mark_symbol,
                "count": len(chosen),
                "gametype": self.gametype,
            }
        )
        return True

    def charge_feature_meter(self):
        self.feature_charge += 1
        threshold_feature = self.config.feature_charge_thresholds.get(self.feature_charge)
        if threshold_feature and threshold_feature not in self.enqueued_features:
            self.feature_queue.append(threshold_feature)
            self.enqueued_features.add(threshold_feature)
            feature_queued_event(self, threshold_feature, self.feature_charge)

        if self.feature_charge >= max(self.config.feature_charge_thresholds):
            if "earth" not in self.enqueued_features:
                self.feature_queue.append("earth")
                self.enqueued_features.add("earth")
                feature_queued_event(self, "earth", self.feature_charge)

    def _tumble_feature_clears(self, positions):
        for reel, row in positions:
            self.board[reel][row].explode = True
        if positions:
            self.tumble_board()
        self.get_special_symbols_on_board()

    def apply_wood_feature(self):
        eligible = self._ordinary_positions()
        requested = get_random_outcome(self.config.wood_wild_count_weights)
        wild_positions = sorted(random.sample(eligible, min(requested, len(eligible))))
        for reel, row in wild_positions:
            self.board[reel][row] = self.create_symbol("W1")

        cleared = set()
        wild_set = set(wild_positions)
        for reel, row in wild_positions:
            neighbours = [
                position
                for position in self._neighbours(self.board, reel, row)
                if position not in wild_set
                and position not in cleared
                and self.board[position[0]][position[1]].name in self.config.symbol_rank
            ]
            if neighbours:
                cleared.add(random.choice(neighbours))
        self._tumble_feature_clears(sorted(cleared))
        feature_applied_event(
            self,
            "wood",
            "arrowRain",
            {
                "wildPositions": self._json_positions(wild_positions),
                "clearedPositions": self._json_positions(cleared),
            },
        )

    def apply_fire_feature(self):
        target_symbol = self._draw_ordinary_symbol_name()
        center = self.config.fire_center
        changed = []
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                if abs(reel - center[0]) != abs(row - center[1]):
                    continue
                if (reel, row) == center:
                    continue
                if self.board[reel][row].check_attribute("wild"):
                    continue
                self.board[reel][row] = self.create_symbol(target_symbol)
                changed.append((reel, row))
        self.board[center[0]][center[1]] = self.create_symbol("W1")
        self.get_special_symbols_on_board()
        feature_applied_event(
            self,
            "fire",
            "diagonalFormation",
            {
                "targetSymbol": target_symbol,
                "centerWild": self._json_positions([center]),
                "changedPositions": self._json_positions(changed),
            },
        )

    def apply_metal_feature(self):
        cleared = [
            (reel, row)
            for reel in range(self.config.num_reels)
            for row in range(self.config.num_rows[reel])
            if self.board[reel][row].name.startswith("L")
        ]
        self._tumble_feature_clears(cleared)
        feature_applied_event(
            self,
            "metal",
            "lowSymbolDestruction",
            {"clearedPositions": self._json_positions(cleared)},
        )

    def apply_water_feature(self):
        present_low = sorted(
            {
                self.board[reel][row].name
                for reel in range(self.config.num_reels)
                for row in range(self.config.num_rows[reel])
                if self.board[reel][row].name.startswith("L")
            }
        )
        source = random.choice(present_low) if present_low else self._draw_ordinary_symbol_name()
        targets = [symbol for symbol in self.config.symbol_rank if symbol != source]
        target = random.choice(targets)
        changed = []
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                if self.board[reel][row].name == source:
                    self.board[reel][row] = self.create_symbol(target)
                    changed.append((reel, row))
        self.get_special_symbols_on_board()
        feature_applied_event(
            self,
            "water",
            "symbolSwap",
            {
                "sourceSymbol": source,
                "targetSymbol": target,
                "changedPositions": self._json_positions(changed),
            },
        )

    def _clear_tracked_wilds(self, tracked_positions):
        cleared = []
        for reel, row in tracked_positions:
            if self.board[reel][row].name == "W1":
                self.board[reel][row] = self.create_symbol(self._draw_ordinary_symbol_name())
                cleared.append((reel, row))
        return cleared

    def place_earth_phase(self, phase, previous_positions=None):
        previous_positions = previous_positions or []
        cleared_previous = self._clear_tracked_wilds(previous_positions)
        positions = set()

        if phase == "3x3":
            left = random.randrange(0, self.config.num_reels - 2)
            top = random.randrange(0, self.config.num_rows[0] - 2)
            positions = {
                (reel, row)
                for reel in range(left, left + 3)
                for row in range(top, top + 3)
            }
        elif phase == "2x2x2":
            candidates = [
                frozenset(
                    {
                        (reel, row),
                        (reel + 1, row),
                        (reel, row + 1),
                        (reel + 1, row + 1),
                    }
                )
                for reel in range(self.config.num_reels - 1)
                for row in range(self.config.num_rows[reel] - 1)
            ]
            first = random.choice(candidates)
            second = random.choice([candidate for candidate in candidates if not candidate.intersection(first)])
            positions = set(first.union(second))
        elif phase == "1x1x9":
            all_positions = [
                (reel, row)
                for reel in range(self.config.num_reels)
                for row in range(self.config.num_rows[reel])
            ]
            positions = set(random.sample(all_positions, 9))
        else:
            raise ValueError(f"未知土系阶段: {phase}")

        overwritten = {
            (reel, row): self.board[reel][row].name
            for reel, row in positions
        }
        for reel, row in positions:
            self.board[reel][row] = self.create_symbol("W1")
        self.get_special_symbols_on_board()
        feature_applied_event(
            self,
            "earth",
            phase,
            {
                "positions": self._json_positions(positions),
                "clearedPrevious": self._json_positions(cleared_previous),
                "overwrittenSymbols": [
                    {
                        "reel": reel,
                        "row": row + 1,
                        "symbol": symbol,
                    }
                    for (reel, row), symbol in sorted(overwritten.items())
                ],
            },
        )
        return sorted(positions)

    def apply_round_feature_multiplier(self):
        feature_count = len(set(self.executed_features))
        multiplier = self.config.feature_round_multipliers[feature_count]
        if multiplier <= 1:
            return
        raw_win = self.win_manager.running_bet_win
        added_win = raw_win * (multiplier - 1)
        self.rtp_components["roundMultiplier"] += added_win
        self.win_manager.update_spinwin(added_win)
        self.win_manager.tumble_win = added_win
        round_multiplier_applied_event(self, multiplier, raw_win, added_win)
        self.evaluate_wincap()

    def emit_component_summary(self):
        rtp_component_summary_event(self)

    def soul_next_threshold(self):
        if self.soul_level >= 7:
            return None
        return self.config.soul_level_thresholds[self.soul_level - 1]

    def initialize_soul_freegame(self, source, w1_positions=None, w2_positions=None):
        """建立一次免费游戏会话；成长状态跨免费旋转保留。"""
        self.tot_fs = self.config.soul_initial_spins
        self.reset_fs_spin()
        self.soul_level = 1
        self.soul_level_progress = 0
        self.soul_total_collected = 0
        self.soul_multiplier = self.config.soul_level_multipliers[0]
        self.soul_positions = set()
        self.soul_consumed = False
        self.soul_winning_symbols = set()
        soul_freespin_trigger_event(
            self,
            source,
            w1_positions=w1_positions,
            w2_positions=w2_positions,
        )
        self.record(
            {
                "kind": "soulFreeSpin",
                "symbol": source,
                "gametype": self.gametype,
            }
        )

    def place_soul_wild(self):
        size = self.soul_level
        left = random.randrange(0, self.config.num_reels - size + 1)
        top = random.randrange(0, self.config.num_rows[0] - size + 1)
        self.soul_positions = {
            (reel, row)
            for reel in range(left, left + size)
            for row in range(top, top + size)
        }
        self.soul_consumed = False
        self.soul_winning_symbols = set()
        soul_wild_placed_event(self)

    def consume_soul_wild(self):
        if not self.soul_consumed or not self.soul_positions:
            return False
        soul_wild_consumed_event(self, self.soul_winning_symbols)
        self.soul_positions = set()
        self.soul_consumed = False
        self.soul_winning_symbols = set()
        return True

    def collect_destiny_wilds(self, positions):
        """只接收本次 reveal/tumble 新出现的 W2 坐标。"""
        positions = sorted(set(positions))
        if not positions:
            return False

        amount = len(positions)
        self.soul_total_collected += amount
        self.soul_level_progress += amount
        destiny_wild_collected_event(self, positions)

        upgraded = False
        while self.soul_level < 7:
            threshold = self.soul_next_threshold()
            if self.soul_level_progress < threshold:
                break
            self.soul_level_progress -= threshold
            self.soul_level += 1
            added_spins = self.config.soul_level_added_spins[self.soul_level - 2]
            self.tot_fs += added_spins
            self.soul_multiplier = self.config.soul_level_multipliers[self.soul_level - 1]
            soul_level_up_event(self, added_spins)
            upgraded = True

        if upgraded:
            self.place_soul_wild()
        return upgraded

    def collect_initial_destiny_wilds(self):
        positions = [
            (reel, row)
            for reel in range(self.config.num_reels)
            for row in range(self.config.num_rows[reel])
            if self.board[reel][row].name == "W2"
        ]
        return self.collect_destiny_wilds(positions)

    def collect_tumble_destiny_wilds(self):
        positions = []
        for reel, symbols in enumerate(self.new_symbols_from_tumble):
            for row, symbol in enumerate(symbols):
                if symbol.name == "W2":
                    positions.append((reel, row))
        return self.collect_destiny_wilds(positions)

    def emit_soul_freespin_summary(self):
        soul_freespin_summary_event(self)
