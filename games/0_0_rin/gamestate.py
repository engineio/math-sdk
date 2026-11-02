from game_override import GameStateOverride
from game_events import update_grid_mult_event


class GameState(GameStateOverride):
    """Core function handling simulation results."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # Reset simulation variables and draw a new board based on the betmode criteria.
            self.reset_book()
            self.draw_board()

            # Smaller chance to Rin Dash immediately after the reveal.
            self.try_rin_dash(after_reveal=True)

            self.get_clusters_update_wins()
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                # After a winning tumble, chance to dash (sticky for remaining tumbles).
                self.try_rin_dash(after_reveal=False)
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board()
            update_grid_mult_event(self)
            # Apply game-specific actions (i.e special symbol attributes before or after evaluation)
            # Night Shift: at least one Rin Dash per freespin, then post-tumble chance.
            self.try_rin_dash(after_reveal=True, force=True)

            self.get_clusters_update_wins()
            self.emit_tumble_win_events()
            self.update_grid_mults()
            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.try_rin_dash(after_reveal=False)
                self.get_clusters_update_wins()
                self.emit_tumble_win_events()
                self.update_grid_mults()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

        self.end_freespin()
