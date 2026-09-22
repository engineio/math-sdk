"""SUGAR STACK — Core game mechanics: Expanding Wilds with Multipliers."""

import random
from game_calculations import GameCalculations
from game_events import (
    expanding_wild_event,
    update_sticky_wilds_event,
    scatter_trigger_event,
)
from src.calculations.statistics import get_random_outcome
from src.events.events import update_freespin_event


class GameExecutables(GameCalculations):

    def find_wild_reels(self) -> list:
        """Find all reels that contain at least one W symbol."""
        wild_reels = []
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                if self.board[reel][row].name == "W":
                    wild_reels.append(reel)
                    break
        return wild_reels

    def expand_wild_reel(self, reel_index: int) -> None:
        """Expand a wild to fill the entire reel column."""
        for row in range(self.config.num_rows[reel_index]):
            sym = self.create_symbol("W")
            self.board[reel_index][row] = sym

    def assign_wild_reel_multiplier(self, reel_index: int) -> int:
        """Assign a random multiplier from the pool to an expanded wild reel."""
        conditions = self.get_current_distribution_conditions()
        mult = get_random_outcome(conditions["wild_mult_values"][self.gametype])

        for row in range(self.config.num_rows[reel_index]):
            sym = self.board[reel_index][row]
            if sym.name == "W":
                sym.assign_attribute({"multiplier": mult})

        return mult

    def apply_expanding_wilds(self) -> list:
        """
        Find all wilds on the board, expand them to fill their reel,
        assign a multiplier per reel, and emit events.
        """
        wild_reels = self.find_wild_reels()
        expanded = []

        for reel_index in wild_reels:
            self.expand_wild_reel(reel_index)
            mult = self.assign_wild_reel_multiplier(reel_index)
            expanded.append({"reel": reel_index, "mult": mult})
            expanding_wild_event(self, reel_index, mult)

        return expanded

    def find_scatter_positions(self) -> list:
        """Find all SC scatter positions on the board (reels 0, 2, 4 only)."""
        positions = []
        for reel in [0, 2, 4]:
            for row in range(self.config.num_rows[reel]):
                if self.board[reel][row].name == "SC":
                    positions.append({"reel": reel, "row": row})
        return positions

    def check_scatter_trigger(self) -> tuple:
        """Check if 3 or more scatters are on the board."""
        positions = self.find_scatter_positions()
        triggered = len(positions) >= 3
        return triggered, positions

    def trigger_freespins_from_scatter(self, scatter_positions: list) -> None:
        """3 scatters → 10 free spins."""
        self.record({
            "kind": "scatter",
            "symbol": "SC",
            "gametype": self.gametype,
        })
        self.tot_fs = 10
        scatter_trigger_event(self, scatter_positions)
        self.run_freespin()

    def restore_sticky_wilds(self) -> None:
        """Restore all sticky wild reels from previous free spins."""
        for sw in self.sticky_wild_reels:
            reel_index = sw["reel"]
            mult = sw["mult"]
            for row in range(self.config.num_rows[reel_index]):
                sym = self.create_symbol("W")
                sym.assign_attribute({"multiplier": mult})
                self.board[reel_index][row] = sym

    def add_sticky_wild_reels(self, expanded_wilds: list) -> None:
        """Add newly expanded wild reels to the sticky list."""
        existing_reels = {sw["reel"] for sw in self.sticky_wild_reels}
        for ew in expanded_wilds:
            if ew["reel"] not in existing_reels:
                self.sticky_wild_reels.append(ew)
                existing_reels.add(ew["reel"])

    def pre_place_expanding_wild(self) -> None:
        """Pre-place one expanding wild on a random reel for super_bonus."""
        available = list(range(self.config.num_reels))
        chosen_reel = random.choice(available)
        self.expand_wild_reel(chosen_reel)
        mult = self.assign_wild_reel_multiplier(chosen_reel)
        entry = {"reel": chosen_reel, "mult": mult}
        self.sticky_wild_reels.append(entry)
        expanding_wild_event(self, chosen_reel, mult)
