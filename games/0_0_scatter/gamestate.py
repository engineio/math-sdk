from game_override import GameStateOverride
from src.calculations.scatter import Scatter


class GameState(GameStateOverride):
    """Gamestate for a single spin"""

    def run_spin(self, sim: int, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()

            self.get_scatterpays_update_wins()
            self.emit_tumble_win_events()  # Transmit win information

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.get_scatterpays_update_wins()
                self.emit_tumble_win_events()  # Transmit win information

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
            # Resets the global multiplier at each spin, except in Super Free Spins (persistent_mult)
            self.update_freespin()
            self.draw_board()

            self.get_scatterpays_update_wins()
            self.emit_tumble_win_events()  # Transmit win information

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.update_global_mult()  # Special mechanic - increase multiplier with every tumble
                
                self.get_scatterpays_update_wins()
                self.emit_tumble_win_events()  # Transmit win information

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

        self.end_freespin()
