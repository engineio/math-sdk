"""SUGAR STACK — State overrides (book reset, special symbol functions, repeat check)."""

from game_executables import GameExecutables
from src.calculations.statistics import get_random_outcome


class GameStateOverride(GameExecutables):

    def reset_book(self) -> None:
        """Reset game-specific state alongside the base book reset."""
        super().reset_book()
        self.sticky_wild_reels = []

    def assign_special_sym_function(self) -> None:
        """
        Register per-symbol attribute functions.
        W gets its multiplier assigned AFTER the board is drawn
        (via apply_expanding_wilds), so this function intentionally
        does nothing — it just satisfies the abstract interface requirement.
        """
        self.special_symbol_functions = {
            "W":  [],
            "SC": [],
        }

    def check_repeat(self) -> None:
        """
        Extend the base repeat check:
        - Honour force_freegame (scatter trigger required).
        - Honour win_criteria for wincap simulations.
        - Ensure non-zero-win criteria actually produce wins.
        """
        if self.repeat is False:
            conditions   = self.get_current_distribution_conditions()
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()

            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True
                return

            if conditions.get("force_freegame") and not self.triggered_freegame:
                self.repeat = True
                return

            if self.criteria not in ("0",) and win_criteria is None and self.win_manager.running_bet_win == 0.0:
                self.repeat = True
