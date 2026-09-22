"""SUGAR STACK — GameState: orchestrates base game and free spins with expanding wilds."""

from copy import deepcopy
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
      1. Restore existing sticky expanded wilds (multipliers re-rolled each spin).
      2. Draw new board, find new wilds → expand + assign multiplier → become sticky.
      3. Evaluate paylines.
      4. Dead spin protection: if sticky wilds present and zero win, re-draw once.
      Repeat for 10 spins (retrigger possible with 3 more scatters).
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
        """10-spin free spins with sticky expanding wilds, escalating multipliers,
        and dead spin protection."""
        self.reset_fs_spin()
        self.sticky_wild_reels = []

        conditions = self.get_current_distribution_conditions()
        pre_placed = conditions.get("pre_placed_wilds", 0)
        if pre_placed > 0:
            self.draw_board(emit_event=False)
            for _ in range(pre_placed):
                self.pre_place_expanding_wild()

        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()

            # Dead spin protection: if sticky wilds exist, allow 1 re-draw on zero win
            max_attempts = 2 if self.sticky_wild_reels else 1
            sticky_snapshot = deepcopy(self.sticky_wild_reels)

            for attempt in range(max_attempts):
                event_mark = len(self.book.events)

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
                    self.tot_fs += 10

                self.win_data = Lines.get_lines(
                    self.board, self.config, global_multiplier=self.global_multiplier
                )

                # If zero win with sticky wilds and we have a retry left, re-draw
                if (self.win_data["totalWin"] == 0
                        and attempt < max_attempts - 1
                        and not triggered):
                    # Rollback: truncate events and restore sticky state
                    self.book.events = self.book.events[:event_mark]
                    self.sticky_wild_reels = deepcopy(sticky_snapshot)
                    continue

                break

            Lines.record_lines_wins(self)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            Lines.emit_linewin_events(self)
            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()
