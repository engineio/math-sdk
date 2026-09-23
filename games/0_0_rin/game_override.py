from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """
    This class is is used to override or extend universal state.py functions.
    e.g: A specific game may have custom book properties to reset
    """

    def reset_book(self):
        # Reset global values used across multiple projects
        super().reset_book()
        # Reset parameters relevant to local game only
        self.tumble_win = 0
        # Clear the position-multiplier grid every spin so a previous freegame's
        # sticky grid cannot leak into a later base spin (the grid is re-zeroed at
        # freegame start by reset_fs_spin and accumulates only within a feature).
        self.reset_grid_mults()
        self.reset_rin_dash_stickies()

    def reset_fs_spin(self):
        super().reset_fs_spin()
        self.reset_grid_mults()
        self.reset_rin_dash_stickies()

    def assign_special_sym_function(self):
        pass

    def check_repeat(self) -> None:
        """Checks if the spin failed a criteria constraint at any point."""
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

            if self.get_current_distribution_conditions()["force_freegame"] and not (self.triggered_freegame):
                self.repeat = True

            if self.win_manager.running_bet_win == 0 and self.criteria != "0":
                self.repeat = True
