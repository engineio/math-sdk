"""SHOGUN — GameState: orchestrates base game and free spins with expanding wilds."""

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
      2. Find wilds → expand to fill reel column → assign random multiplier.
      3. Evaluate paylines (wild multipliers multiply together on multi-wild lines).
      4. If 3 SC scatters on reels 0/2/4 → trigger 10 free spins.

    Free spins:
      1. Restore existing sticky expanded wilds (multipliers persist).
      2. Draw new board, find new wilds → expand + assign multiplier → become sticky.
      3. Evaluate paylines.
      Repeat for 10 spins (retrigger possible with 3 more scatters).
    """

    # ── Base game ─────────────────────────────────────────────────────────────

    def run_spin(self, sim, simulation_seed=None) -> None:
        self.reset_seed(sim)
        self.repeat = True

        while self.repeat:
            self.reset_book()
            self.draw_board(emit_event=True)

            # Find and expand wilds, assign multipliers
            self.apply_expanding_wilds()

            # Evaluate paylines
            self.win_data = Lines.get_lines(
                self.board, self.config, global_multiplier=self.global_multiplier
            )
            Lines.record_lines_wins(self)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            Lines.emit_linewin_events(self)
            self.win_manager.update_gametype_wins(self.gametype)

            # Scatter trigger: 3 SC on reels 0, 2, 4
            triggered, scatter_positions = self.check_scatter_trigger()
            if triggered:
                self.trigger_freespins_from_scatter(scatter_positions)

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    # ── Free spins with sticky expanding wilds ────────────────────────────────

    def run_freespin(self) -> None:
        """10-spin free spins with sticky expanding wilds and multipliers."""
        self.reset_fs_spin()
        self.sticky_wild_reels = []

        # Super buy bonus: pre-place 1 expanding wild before free spins start
        conditions = self.get_current_distribution_conditions()
        pre_placed = conditions.get("pre_placed_wilds", 0)
        if pre_placed > 0:
            # Draw initial board for pre-placement context
            self.draw_board(emit_event=False)
            for _ in range(pre_placed):
                self.pre_place_expanding_wild()

        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            self.draw_board(emit_event=False)

            # 1. Restore sticky wilds from previous spins
            self.restore_sticky_wilds()
            if self.sticky_wild_reels:
                update_sticky_wilds_event(self)

            # 2. Find new wilds on non-sticky reels, expand + assign multipliers
            expanded = self.apply_expanding_wilds()

            # 3. New expanded wilds become sticky
            if expanded:
                self.add_sticky_wild_reels(expanded)

            # Emit board reveal
            reveal_event(self)

            # 4. Check for scatter retrigger (3 SC → +10 free spins)
            triggered, scatter_positions = self.check_scatter_trigger()
            if triggered:
                self.tot_fs += 10

            # 5. Evaluate paylines
            self.win_data = Lines.get_lines(
                self.board, self.config, global_multiplier=self.global_multiplier
            )
            Lines.record_lines_wins(self)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            Lines.emit_linewin_events(self)
            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()
