"""AURA FARM — GameState: base game + HARVEST SEASON free spins with Aura Farming Wilds."""

from game_override import GameStateOverride
from src.calculations.lines import Lines
from src.calculations.statistics import get_random_outcome
from src.events.events import reveal_event
from game_events import (
    expanding_wild_event,
    update_sticky_wilds_event,
)


class GameState(GameStateOverride):
    """
    Base game flow:
      1. Draw board from reel strips.
      2. Find seeds (W) -> expand to fill reel column -> assign multiplier.
      3. Evaluate paylines (seed multipliers MULTIPLY together on multi-seed lines).
      4. 3 SC (golden yuzu) on reels 0/2/4 -> HARVEST SEASON (10 free spins).

    HARVEST SEASON (the signature):
      1. AURA FARMING: every surviving seed levels up first (x2 per spin, cap x128).
      2. Restore sticky seeds, draw new board, new seeds stick at their landing roll.
      3. Evaluate paylines.
      MONSOON (retrigger, 3 SC): +5 spins AND every seed levels up instantly.
    """

    def run_spin(self, sim, simulation_seed=None) -> None:
        self.reset_seed(sim)
        self.repeat = True

        while self.repeat:
            self.reset_book()
            self.draw_board(emit_event=True)

            self.apply_expanding_wilds()

            self.win_data = Lines.get_lines(
                self.board, self.config, global_multiplier=self.global_multiplier
            )
            Lines.record_lines_wins(self)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            Lines.emit_linewin_events(self)
            self.win_manager.update_gametype_wins(self.gametype)

            triggered, scatter_positions = self.check_scatter_trigger()
            if triggered:
                self.trigger_freespins_from_scatter(scatter_positions)

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self) -> None:
        """HARVEST SEASON — seeds never reset, and they farm aura every spin."""
        self.reset_fs_spin()
        self.sticky_wild_reels = []

        conditions = self.get_current_distribution_conditions()
        pre_placed = conditions.get("pre_placed_wilds", 0)
        pre_level = conditions.get("pre_placed_level", 1)
        if pre_placed > 0:
            self.draw_board(emit_event=False)
            for _ in range(pre_placed):
                self.pre_place_expanding_wild(level=pre_level)

        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()

            # AURA FARMING: the farm waters ONE seed at the start of every spin
            if self.fs > 1:
                self.level_up_sticky_wilds()

            self.draw_board(emit_event=False)

            self.restore_sticky_wilds()
            if self.sticky_wild_reels:
                update_sticky_wilds_event(self)

            expanded = self.apply_expanding_wilds()

            if expanded:
                self.add_sticky_wild_reels(expanded)

            reveal_event(self)

            triggered, scatter_positions = self.check_scatter_trigger()
            if triggered:
                # MONSOON: +5 spins and EVERY planted seed levels up instantly
                self.tot_fs += 5
                self.level_up_sticky_wilds(all_seeds=True)

            self.win_data = Lines.get_lines(
                self.board, self.config, global_multiplier=self.global_multiplier
            )
            Lines.record_lines_wins(self)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            Lines.emit_linewin_events(self)
            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()
