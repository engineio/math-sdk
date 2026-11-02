"""AURA FARM — Core mechanics: Aura Farming Wilds (sticky, level-up, multiply together)."""

import random
from game_calculations import GameCalculations
from game_events import (
    expanding_wild_event,
    update_sticky_wilds_event,
    scatter_trigger_event,
)
from src.calculations.statistics import get_random_outcome
from src.events.events import update_freespin_event

AURA_CAP = 128  # max seed level multiplier (x2 -> x128)


class GameExecutables(GameCalculations):

    def find_wild_reels(self) -> list:
        """Find all reels that contain at least one W (aura seed) symbol."""
        wild_reels = []
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                if self.board[reel][row].name == "W":
                    wild_reels.append(reel)
                    break
        return wild_reels

    def expand_wild_reel(self, reel_index: int) -> None:
        """Expand a seed to fill the entire reel column."""
        for row in range(self.config.num_rows[reel_index]):
            sym = self.create_symbol("W")
            self.board[reel_index][row] = sym

    def assign_wild_reel_multiplier(self, reel_index: int) -> int:
        """Assign a random multiplier from the pool to an expanded seed reel."""
        conditions = self.get_current_distribution_conditions()
        mult = get_random_outcome(conditions["wild_mult_values"][self.gametype])

        for row in range(self.config.num_rows[reel_index]):
            sym = self.board[reel_index][row]
            if sym.name == "W":
                sym.assign_attribute({"multiplier": mult})

        return mult

    def apply_expanding_wilds(self) -> list:
        """
        Find all seeds on the board, expand them to fill their reel,
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
        """Find all SC (golden yuzu) positions on the board (reels 0, 2, 4 only)."""
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
        """3 scatters -> 10 free spins (HARVEST SEASON)."""
        self.record({
            "kind": "scatter",
            "symbol": "SC",
            "gametype": self.gametype,
        })
        self.tot_fs = 10
        scatter_trigger_event(self, scatter_positions)
        self.run_freespin()

    # ── AURA FARMING ─────────────────────────────────────────────────
    def level_up_sticky_wilds(self, all_seeds: bool = False) -> None:
        """Water the farm: a seed levels up (multiplier doubles, cap x128).

        Per spin the farm waters ONE random seed; a MONSOON (retrigger)
        waters ALL of them at once. Doubling every seed every spin proved
        geometrically unreachable for the optimizer fences (avg-win blowup
        with 3 greenhouse seeds), so single-watering is the balanced form —
        seeds still walk x2 -> x128 and MULTIPLY together on a line.
        """
        if not self.sticky_wild_reels:
            return
        if all_seeds:
            for sw in self.sticky_wild_reels:
                sw["mult"] = min(sw["mult"] * 2, AURA_CAP)
        else:
            sw = random.choice(self.sticky_wild_reels)
            sw["mult"] = min(sw["mult"] * 2, AURA_CAP)

    def restore_sticky_wilds(self) -> None:
        """Restore all sticky seed reels from previous free spins."""
        for sw in self.sticky_wild_reels:
            reel_index = sw["reel"]
            mult = sw["mult"]
            for row in range(self.config.num_rows[reel_index]):
                sym = self.create_symbol("W")
                sym.assign_attribute({"multiplier": mult})
                self.board[reel_index][row] = sym

    def add_sticky_wild_reels(self, expanded_wilds: list) -> None:
        """Add newly expanded seed reels to the sticky list."""
        existing_reels = {sw["reel"] for sw in self.sticky_wild_reels}
        for ew in expanded_wilds:
            if ew["reel"] not in existing_reels:
                self.sticky_wild_reels.append(ew)
                existing_reels.add(ew["reel"])

    def pre_place_expanding_wild(self, level: int = 1) -> None:
        """Pre-place one seed on a random reel (GREENHOUSE super buy).

        level > 1 boosts the rolled multiplier by doubling per extra level
        (level 2 == one level-up already applied), capped at AURA_CAP.
        """
        available = [r for r in range(self.config.num_reels)
                     if r not in {sw["reel"] for sw in self.sticky_wild_reels}]
        chosen_reel = random.choice(available)
        self.expand_wild_reel(chosen_reel)
        mult = self.assign_wild_reel_multiplier(chosen_reel)
        for _ in range(max(0, level - 1)):
            mult = min(mult * 2, AURA_CAP)
        # re-stamp boosted multiplier onto the board symbols
        for row in range(self.config.num_rows[chosen_reel]):
            sym = self.board[chosen_reel][row]
            if sym.name == "W":
                sym.assign_attribute({"multiplier": mult})
        entry = {"reel": chosen_reel, "mult": mult}
        self.sticky_wild_reels.append(entry)
        expanding_wild_event(self, chosen_reel, mult)
