"""Fight Club — Core mechanics: KO Reels multiplier + Death Match fighter->WILD."""

import random
from game_calculations import GameCalculations
from game_events import ko_mult_event, fighter_wild_event
from src.events.events import update_freespin_event


class GameExecutables(GameCalculations):
    """Game-specific grouped functions for Fight Club."""

    def get_current_mode_name(self):
        """Get the current bet mode name."""
        return self.config.bet_modes[self.betmode].get_name()

    def reset_ko_mult(self):
        """Reset KO multiplier to the starting value for the current mode."""
        if not hasattr(self, "betmode") or self.betmode is None:
            self.global_multiplier = 1
            return
        mode = self.get_current_mode_name()
        self.global_multiplier = self.config.ko_mult_start.get(mode, 1)

    def increment_ko_mult(self):
        """Increment KO multiplier by the mode's increment value."""
        mode = self.get_current_mode_name()
        increment = self.config.ko_mult_increment.get(mode, 1)
        self.global_multiplier += increment
        self.global_multiplier = min(self.global_multiplier, self.config.maximum_board_mult)
        ko_mult_event(self)

    def should_ko_carry_over(self):
        """Check if KO multiplier carries over between spins in current mode."""
        mode = self.get_current_mode_name()
        return self.config.ko_mult_carries_over.get(mode, False)

    def is_death_match(self):
        """Check if current distribution has death_match flag."""
        conditions = self.get_current_distribution_conditions()
        return conditions.get("death_match", False)

    def convert_random_fighter_to_wild(self):
        """
        Death Match: pick a random fighter symbol and convert
        all instances on the board to WILD.
        """
        fighter = random.choice(self.config.fighter_symbols)
        converted_positions = []

        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                if self.board[reel][row].name == fighter:
                    self.board[reel][row] = self.create_symbol("W")
                    converted_positions.append({"reel": reel, "row": row})

        if converted_positions:
            fighter_wild_event(self, fighter, converted_positions)

        return fighter, converted_positions

    def get_freespin_count_for_mode(self):
        """Get fixed free spin count from freespin_override, or from scatter triggers."""
        conditions = self.get_current_distribution_conditions()
        override = conditions.get("freespin_override", None)
        if override is not None:
            return override
        scatter_count = self.count_special_symbols("scatter")
        return self.config.freespin_triggers[self.gametype].get(scatter_count, 8)

    def update_freespin(self) -> None:
        """Called before a new reveal during freegame."""
        self.fs += 1
        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.win_data = {}
