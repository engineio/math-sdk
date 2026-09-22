"""FRACTURE: GODS DIVIDED — Game Configuration.

Re-themes the approved Sugar Stack engine (expanding sticky multiplier-wilds +
free spins + buy modes) onto a 5x3 / 10-line Greek-gods slot:
  - Base game: a random reel can FRACTURE into a full WILD column carrying a ×N multiplier.
  - Free spins (the "blessing"):
      * bonus       -> TIDE OF POSEIDON: sticky expanding multiplier-wild reels (engine default).
      * super_bonus -> ZEUS'S WRATH: starts with a pre-placed sticky wild, richer mult pool.
  - 3 Scatters trigger the blessing (server decides which on a natural trigger; the two
    BUY modes let the player pick the blessing directly — same pattern as Sugar Stack's
    bonus / super_bonus buys).
"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "fracture_gods_divided"
        self.provider_number = 1
        self.working_name = "Fracture: Gods Divided"
        self.wincap = 10000.0   # matches the proven optimizer win-range buckets (game_optimization.py)
        self.win_type = "lines"
        self.rtp = 0.9600
        try:
            self.construct_paths(self.game_id)
        except TypeError:
            self.construct_paths()

        # 5×3 grid
        self.num_reels = 5
        self.num_rows = [3] * self.num_reels

        # ── Paytable (pay × line bet for 3/4/5 of a kind) ─────────────
        # Wild pays as the top symbol (Zeus).
        self.paytable = {
            (5, "W"): 25,        (4, "W"): 8,         (3, "W"): 2,
            (5, "zeus"): 25,     (4, "zeus"): 8,      (3, "zeus"): 2,
            (5, "poseidon"): 18, (4, "poseidon"): 5,  (3, "poseidon"): 1.5,
            (5, "bolt"): 12,     (4, "bolt"): 3,      (3, "bolt"): 1,
            (5, "trident"): 10,  (4, "trident"): 2.5, (3, "trident"): 0.8,
            (5, "A"): 5,         (4, "A"): 1.5,       (3, "A"): 0.5,
            (5, "K"): 4,         (4, "K"): 1.2,       (3, "K"): 0.4,
            (5, "Q"): 3,         (4, "Q"): 1.0,       (3, "Q"): 0.3,
            (5, "J"): 2.5,       (4, "J"): 0.8,       (3, "J"): 0.25,
        }

        # ── 10 Paylines on a 5×3 grid (rows 0/1/2) ────────────────────
        self.paylines = {
            1:  [1, 1, 1, 1, 1],
            2:  [0, 0, 0, 0, 0],
            3:  [2, 2, 2, 2, 2],
            4:  [0, 1, 2, 1, 0],
            5:  [2, 1, 0, 1, 2],
            6:  [0, 0, 1, 2, 2],
            7:  [2, 2, 1, 0, 0],
            8:  [1, 0, 1, 2, 1],
            9:  [1, 2, 1, 0, 1],
            10: [0, 1, 1, 1, 2],
        }

        self.include_padding = True

        # W is wild (carries multiplier), SC is scatter (on reels 0, 2, 4 only)
        self.special_symbols = {
            "wild":       ["W"],
            "multiplier": ["W"],
            "scatter":    ["SC"],
        }

        # 3 SC scatters → 8 free spins (base and free game; retrigger possible)
        self.freespin_triggers = {
            self.basegame_type: {3: 8},
            self.freegame_type: {3: 8},
        }
        self.anticipation_triggers = {
            self.basegame_type: 2,
            self.freegame_type: 2,
        }

        # ── Reels ─────────────────────────────────────────────────────
        reel_files = {"BR0": "BR0.csv", "FR0": "FR0.csv"}
        self.reels = {}
        for name, filename in reel_files.items():
            self.reels[name] = self.read_reels_csv(os.path.join(self.reels_path, filename))

        self.padding_reels = {
            self.basegame_type: self.reels["BR0"],
            self.freegame_type: self.reels["FR0"],
        }

        # ── Wild Multiplier Pools (weighted) ──────────────────────────
        wild_mult_base = {2: 200, 3: 80, 5: 20, 10: 5, 20: 2, 50: 1, 100: 1}
        wild_mult_bonus = {2: 200, 3: 80, 5: 30, 10: 10, 20: 5, 50: 2, 100: 1}

        # ── Shared condition templates ────────────────────────────────
        def _cond(force_fg, force_wincap, reel_base, reel_free=None):
            c = {
                "reel_weights": {self.basegame_type: {reel_base: 1}},
                "wild_mult_values": {self.basegame_type: wild_mult_base},
                "force_freegame": force_fg,
                "force_wincap":   force_wincap,
            }
            if reel_free:
                c["reel_weights"][self.freegame_type] = {reel_free: 1}
                c["wild_mult_values"][self.freegame_type] = wild_mult_bonus
            return c

        freegame_cond = _cond(force_fg=True, force_wincap=False, reel_base="BR0", reel_free="FR0")
        freegame_cond["scatter_triggers"] = {3: 1}

        basegame_cond = _cond(force_fg=False, force_wincap=False, reel_base="BR0", reel_free="FR0")
        zerowin_cond  = _cond(force_fg=False, force_wincap=False, reel_base="BR0", reel_free="FR0")

        wincap_cond = _cond(force_fg=True, force_wincap=True, reel_base="BR0", reel_free="FR0")
        wincap_cond["scatter_triggers"] = {3: 1}
        wincap_cond["wild_mult_values"][self.freegame_type] = {2: 150, 3: 60, 5: 30, 10: 15, 20: 8, 50: 3, 100: 2}

        # POSEIDON buy — sticky multiplier-wild flood (engine default free game)
        bonus_cond = {
            **freegame_cond,
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
            "scatter_triggers": {3: 1},
        }
        # ZEUS buy — starts with a pre-placed sticky wild ("the storm rises")
        super_bonus_cond = {
            **freegame_cond,
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
            "scatter_triggers": {3: 1},
            "pre_placed_wilds": 1,
        }

        # ── Bet Modes ─────────────────────────────────────────────────
        maxwins = {"base": self.wincap, "bonus": self.wincap, "super_bonus": self.wincap}

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=maxwins["base"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(criteria="wincap",   quota=0.001, win_criteria=maxwins["base"], conditions=wincap_cond),
                    Distribution(criteria="freegame", quota=0.10,  conditions=freegame_cond),
                    Distribution(criteria="0",        quota=0.40,  win_criteria=0.0, conditions=zerowin_cond),
                    Distribution(criteria="basegame", quota=0.489, conditions=basegame_cond),
                ],
            ),
            BetMode(
                name="double_chance",
                cost=1.5,
                rtp=self.rtp,
                max_win=maxwins["base"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(criteria="wincap",   quota=0.001, win_criteria=maxwins["base"], conditions=wincap_cond),
                    Distribution(criteria="freegame", quota=0.20,  conditions=freegame_cond),
                    Distribution(criteria="0",        quota=0.35,  win_criteria=0.0, conditions=zerowin_cond),
                    Distribution(criteria="basegame", quota=0.449, conditions=basegame_cond),
                ],
            ),
            BetMode(
                name="bonus",
                cost=100.0,
                rtp=self.rtp,
                max_win=maxwins["bonus"],
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap",   quota=0.001, win_criteria=maxwins["bonus"], conditions=wincap_cond),
                    Distribution(criteria="freegame", quota=0.999, conditions=bonus_cond),
                ],
            ),
            BetMode(
                name="super_bonus",
                cost=200.0,
                rtp=self.rtp,
                max_win=maxwins["super_bonus"],
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(criteria="wincap",   quota=0.001, win_criteria=maxwins["super_bonus"], conditions=wincap_cond),
                    Distribution(criteria="freegame", quota=0.999, conditions=super_bonus_cond),
                ],
            ),
        ]
