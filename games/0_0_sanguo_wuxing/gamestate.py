"""《三国五行传》M2c 基础游戏与成长武魂免费游戏状态机。"""

from game_override import GameStateOverride
from src.events.events import enter_bonus_event


class GameState(GameStateOverride):
    def _guard_round_limits(self):
        if self.cascade_steps > self.config.max_cascade_steps:
            raise RuntimeError("超过单局最大连锁步骤数")
        if len(self.book.events) > self.config.max_book_events:
            raise RuntimeError("超过单局最大 Book Event 数")

    def _evaluate_stable_board(self, source):
        self.current_win_source = source
        if self.gametype == self.config.basegame_type:
            self.check_dual_wild_trigger_candidate()
            self.prepare_mega_groups()
        else:
            self.mega_groups = []
        self.get_clusters_update_wins()
        self.emit_tumble_win_events()
        if self.win_data["totalWin"] > 0:
            self.cascade_steps += 1
            if self.gametype == self.config.basegame_type:
                if (
                    self.config.feature_cascades_charge_meter
                    or source in {"natural", "rescue", "return"}
                ):
                    self.charge_feature_meter()
                self.prepare_return_wilds()
        self._guard_round_limits()

    def resolve_cascades(self, source):
        active_source = source
        self._evaluate_stable_board(active_source)
        while self.win_data["totalWin"] > 0 and not self.wincap_triggered:
            if self.gametype == self.config.freegame_type:
                self.consume_soul_wild()
            self.tumble_game_board()
            if self.gametype == self.config.freegame_type:
                self.collect_tumble_destiny_wilds()
            elif self.apply_pending_return_wilds():
                active_source = "return"
            self._evaluate_stable_board(active_source)

    def execute_queued_features(self):
        while self.feature_queue and not self.wincap_triggered:
            feature = self.feature_queue.pop(0)
            if feature in self.executed_features:
                continue
            self.executed_features.append(feature)
            self.record(
                {
                    "kind": "featureExecuted",
                    "symbol": feature,
                    "gametype": self.gametype,
                }
            )

            if feature == "wood":
                self.apply_wood_feature()
                self.resolve_cascades("wood")
            elif feature == "fire":
                self.apply_fire_feature()
                self.resolve_cascades("fire")
            elif feature == "metal":
                self.apply_metal_feature()
                self.resolve_cascades("metal")
            elif feature == "water":
                self.apply_water_feature()
                self.resolve_cascades("water")
            elif feature == "earth":
                tracked_positions = []
                for phase in ("3x3", "2x2x2", "1x1x9"):
                    if self.wincap_triggered:
                        break
                    tracked_positions = self.place_earth_phase(phase, tracked_positions)
                    self.resolve_cascades("earth")
            else:
                raise ValueError(f"未知功能: {feature}")
            self._guard_round_limits()

    def run_base_round(self):
        self.draw_board()
        self.activate_return_mark()
        self.resolve_cascades("natural")

        if (
            self.cascade_steps == 0
            and not self.wincap_triggered
            and self.attempt_rescue()
        ):
            self.resolve_cascades("rescue")

        self.execute_queued_features()
        self.apply_round_feature_multiplier()
        self.set_end_tumble_event()
        self.win_manager.update_gametype_wins(self.gametype)

    def run_freespin(self):
        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            self.cascade_steps = 0
            self.draw_board()
            upgraded = self.collect_initial_destiny_wilds()
            if not upgraded:
                self.place_soul_wild()
            self.resolve_cascades("freeNatural")
            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

        self.emit_soul_freespin_summary()
        self.end_freespin()

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim, seed_override=simulation_seed)
        self.repeat = True
        while self.repeat:
            self.reset_book()

            if self.betmode == "bonus":
                self.bonus_type = "soulBonusBuy"
                enter_bonus_event(self)
                self.initialize_soul_freegame("bonusBuy")
                self.run_freespin()
            else:
                self.run_base_round()
                if self.dual_wild_seen and not self.wincap_triggered:
                    self.initialize_soul_freegame(
                        "dualWild",
                        self.dual_wild_w1_positions,
                        self.dual_wild_w2_positions,
                    )
                    self.run_freespin()

            self.emit_component_summary()
            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()
