"""Fight Club — GameState: cascade cluster pays with KO Reels multiplier."""

from game_override import GameStateOverride
from game_events import ko_mult_event
from src.events.events import fs_trigger_event


class GameState(GameStateOverride):
    """
    Base game flow:
      1. Draw board from reel strips
      2. Find clusters (5+ adjacent matching symbols)
      3. If wins: shatter winning symbols, drop new ones (cascade/tumble)
      4. Each cascade increments KO Reels multiplier
      5. Repeat until no more wins
      6. If 4+ scatters: trigger free spins

    Free spins (3 types):
      Exhibition (8 FS): KO starts at 2x, resets each spin
      Title Fight (10 FS): KO starts at 1x, carries over between spins
      Death Match (5 FS): KO starts at 3x, +2x per cascade, carries over,
                          random fighter->WILD each spin
    """

    def run_spin(self, sim, simulation_seed=None) -> None:
        self.reset_seed(sim)
        self.repeat = True

        while self.repeat:
            self.reset_book()
            self.draw_board()

            # Emit initial KO multiplier
            ko_mult_event(self)

            # Evaluate clusters and cascade
            self.get_clusters_update_wins()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered:
                # Each cascade = KO multiplier increases
                self.increment_ko_mult()
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            # Check scatter trigger for free spins
            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin_from_base(self, scatter_key="scatter") -> None:
        """Override to use mode-specific free spin count."""
        self.record(
            {
                "kind": self.count_special_symbols(scatter_key),
                "symbol": scatter_key,
                "gametype": self.gametype,
            }
        )
        # Set FS count: use freespin_override if set, otherwise scatter-based
        self.tot_fs = self.get_freespin_count_for_mode()

        basegame_trigger, freegame_trigger = True, False
        fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=freegame_trigger)

        self.run_freespin()

    def run_freespin(self):
        """Free spins with KO Reels multiplier and optional Death Match mechanic."""
        self.reset_fs_spin()

        death_match = self.is_death_match()

        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()

            # Reset KO mult per spin if mode doesn't carry over
            if not self.should_ko_carry_over():
                self.reset_ko_mult()

            self.draw_board()

            # Death Match: convert a random fighter to WILD each spin
            if death_match:
                self.convert_random_fighter_to_wild()

            # Emit initial KO multiplier for this spin
            ko_mult_event(self)

            # Evaluate clusters and cascade
            self.get_clusters_update_wins()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not self.wincap_triggered:
                self.increment_ko_mult()
                self.tumble_game_board()
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            # Check for retrigger
            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

        self.end_freespin()
