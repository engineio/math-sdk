"""

"""

from copy import copy

from game_calculations import GameCalculations
from src.calculations.scatter import Scatter
from game_events import send_mult_info_event
from src.events.events import (
    set_win_event,
    set_total_event,
    fs_trigger_event,
    update_tumble_win_event,
    update_global_mult_event,
    update_freespin_event,
)


class GameExecutables(GameCalculations):
    """Game specific executable functions. Used for grouping commonly used/repeated applications."""

    def set_end_tumble_event(self):
        """After all tumbling events have finished, multiply tumble-win by sum of mult symbols."""
        if self.gametype == self.config.freegame_type:  # Only multipliers in freegame
            board_mult, mult_info = self.get_board_multipliers()
            base_tumble_win = copy(self.win_manager.spin_win)
            self.win_manager.set_spin_win(base_tumble_win * board_mult)
            if self.win_manager.spin_win > 0 and len(mult_info) > 0:
                send_mult_info_event(
                    self,
                    board_mult,
                    mult_info,
                    base_tumble_win,
                    self.win_manager.spin_win,
                )
                update_tumble_win_event(self)

        if self.win_manager.spin_win > 0:
            set_win_event(self)
        set_total_event(self)

    def update_freespin_amount(self, scatter_key: str = "scatter"):
        """Update current and total freespin number and emit event."""
        self.tot_fs = self.count_special_symbols(scatter_key) * 2
        if self.gametype == self.config.basegame_type:
            basegame_trigger, freegame_trigger = True, False
        else:
            basegame_trigger, freegame_trigger = False, True
        fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=freegame_trigger)

    def get_scatterpays_update_wins(self):
        """Return the board since we are assigning the 'explode' attribute."""
        self.win_data = Scatter.get_scatterpay_wins(
            self.config, self.board, global_multiplier=self.global_multiplier
        )  # Evaluate wins, self.board is modified in-place
        Scatter.record_scatter_wins(self)
        self.win_manager.tumble_win = self.win_data["totalWin"]
        self.win_manager.update_spinwin(self.win_data["totalWin"])  # Update wallet

    def update_freespin(self) -> None:
        """Called before a new reveal during freegame."""
        self.fs += 1
        update_freespin_event(self)
        # Free Spins (base, ante and the 200x bonus) restart the global multiplier at x1 on every spin.
        # Super Free Spins (the 500x super_bonus, "persistent_mult") keep it for the whole feature;
        # reset_fs_spin starts it at x1 when the feature begins. The event is sent either way, so the
        # client always knows the multiplier a spin starts with.
        if not self.get_current_distribution_conditions().get("persistent_mult", False):
            self.global_multiplier = 1
        update_global_mult_event(self)
        self.win_manager.reset_spin_win()
        self.tumblewin_mult = 0
        self.win_data = {}
