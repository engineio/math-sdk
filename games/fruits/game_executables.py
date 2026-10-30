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

    def _get_wild_mult_pool(self) -> dict:
        """Get the correct multiplier pool based on game phase.

        During free spins with escalation configured:
          Spins 1-4  → early pool  (mostly small mults)
          Spins 5-7  → mid pool    (balanced)
          Spins 8-10 → late pool   (big mults dominate)
        Falls back to the standard pool if no escalation is set.
        """
        conditions = self.get_current_distribution_conditions()
        escalation = conditions.get("wild_mult_escalation")

        if escalation and hasattr(self, "fs") and hasattr(self, "tot_fs") and self.tot_fs > 0:
            progress = self.fs / self.tot_fs
            if progress <= 0.4:
                return escalation["early"]
            elif progress <= 0.7:
                return escalation["mid"]
            else:
                return escalation["late"]

        return conditions["wild_mult_values"][self.gametype]

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
        """Assign a random multiplier from the escalation-aware pool."""
        pool = self._get_wild_mult_pool()
        mult = get_random_outcome(pool)

        for row in range(self.config.num_rows[reel_index]):
            sym = self.board[reel_index][row]
            if sym.name == "W":
                sym.assign_attribute({"multiplier": mult})

        return mult

    def apply_expanding_wilds(self) -> list:
        """
        Find all wilds on the board, expand them to fill their reel,
        assign a multiplier per reel, and emit events.
        Skips reels already restored by restore_sticky_wilds() to avoid
        re-rolling their multiplier (which would mismatch the updateStickyWilds event).
        """
        wild_reels = self.find_wild_reels()
        expanded = []
        existing_sticky = {sw["reel"] for sw in self.sticky_wild_reels} if hasattr(self, 'sticky_wild_reels') else set()

        for reel_index in wild_reels:
            if reel_index in existing_sticky:
                continue
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
        """Restore sticky wild reels with RE-ROLLED multipliers each spin."""
        pool = self._get_wild_mult_pool()

        for sw in self.sticky_wild_reels:
            reel_index = sw["reel"]
            # Re-roll multiplier from current phase pool
            new_mult = get_random_outcome(pool)
            sw["mult"] = new_mult

            for row in range(self.config.num_rows[reel_index]):
                sym = self.create_symbol("W")
                sym.assign_attribute({"multiplier": new_mult})
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
