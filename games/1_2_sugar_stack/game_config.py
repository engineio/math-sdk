"""SUGAR STACK — Game Configuration."""

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
        self.game_id = "1_2_sugar_stack"
        self.provider_number = 1
        self.working_name = "Sugar Stack"
        self.wincap = 10000.0
        self.win_type = "lines"
        self.rtp = 0.9600
        try:
            self.construct_paths(self.game_id)
        except TypeError:
            self.construct_paths()

        # 5×5 grid
        self.num_reels = 5
        self.num_rows = [5] * self.num_reels

        # ── Paytable ──────────────────────────────────────────────
        # Wild pays same as top symbol (watermelon)
        self.paytable = {
            # Wild
            (5, "W"): 15,   (4, "W"): 6,    (3, "W"): 2,
            # Premium symbols
            (5, "watermelon"):  15,   (4, "watermelon"):  6,    (3, "watermelon"):  2,
            (5, "grape"):       10,   (4, "grape"):       4,    (3, "grape"):       1.5,
            (5, "orange"):       8,   (4, "orange"):      3,    (3, "orange"):      1,
            (5, "cherry"):       5,   (4, "cherry"):      2,    (3, "cherry"):      0.8,
            (5, "plum"):         4,   (4, "plum"):        1.5,  (3, "plum"):        0.5,
            (5, "lemon"):        3,   (4, "lemon"):       1,    (3, "lemon"):       0.3,
            # Low-pay symbols
            (5, "A"): 2,    (4, "A"): 0.6,   (3, "A"): 0.2,
            (5, "K"): 1.5,  (4, "K"): 0.4,   (3, "K"): 0.15,
            (5, "Q"): 1,    (4, "Q"): 0.3,    (3, "Q"): 0.1,
            (5, "J"): 0.8,  (4, "J"): 0.2,    (3, "J"): 0.1,
            (5, "10"): 0.8, (4, "10"): 0.2,   (3, "10"): 0.1,
        }

        # ── 20 Paylines on 5×5 grid ───────────────────────────────
        self.paylines = {
            1:  [2, 2, 2, 2, 2],
            2:  [0, 0, 0, 0, 0],
            3:  [4, 4, 4, 4, 4],
            4:  [0, 1, 2, 1, 0],
            5:  [4, 3, 2, 3, 4],
            6:  [0, 0, 1, 2, 2],
            7:  [4, 4, 3, 2, 2],
            8:  [1, 0, 1, 0, 1],
            9:  [3, 4, 3, 4, 3],
            10: [1, 1, 0, 1, 1],
            11: [3, 3, 4, 3, 3],
            12: [2, 1, 0, 1, 2],
            13: [2, 3, 4, 3, 2],
            14: [0, 1, 1, 1, 0],
            15: [4, 3, 3, 3, 4],
            16: [1, 2, 3, 2, 1],
            17: [3, 2, 1, 2, 3],
            18: [0, 2, 4, 2, 0],
            19: [4, 2, 0, 2, 4],
            20: [2, 0, 2, 0, 2],
        }

        self.include_padding = True

        # W is wild, SC is scatter (on reels 0, 2, 4 only)
        self.special_symbols = {
            "wild":       ["W"],
            "multiplier": ["W"],
            "scatter":    ["SC"],
        }

        # Scatter trigger: 3 SC → 10 free spins (base and free game)
        self.freespin_triggers = {
            self.basegame_type: {3: 10},
            self.freegame_type: {3: 10},
        }
        self.anticipation_triggers = {
            self.basegame_type: 2,
            self.freegame_type: 2,
        }

        # ── Reels ─────────────────────────────────────────────────
        reel_files = {"BR0": "BR0.csv", "FR0": "FR0.csv"}
        self.reels = {}
        for name, filename in reel_files.items():
            self.reels[name] = self.read_reels_csv(os.path.join(self.reels_path, filename))

        self.padding_reels = {
            self.basegame_type: self.reels["BR0"],
            self.freegame_type: self.reels["FR0"],
        }

        # ── Expanding Wild Multiplier Pool ────────────────────────
        wild_mult_base = {2: 200, 3: 80, 5: 20, 10: 5, 20: 2, 50: 1, 100: 1}
        wild_mult_bonus = {2: 200, 3: 80, 5: 30, 10: 10, 20: 5, 50: 2, 100: 1}

        # ── Shared condition templates ────────────────────────────
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

        freegame_cond = _cond(
            force_fg=True, force_wincap=False,
            reel_base="BR0", reel_free="FR0",
        )
        freegame_cond["scatter_triggers"] = {3: 1}

        basegame_cond = _cond(
            force_fg=False, force_wincap=False,
            reel_base="BR0", reel_free="FR0",
        )
        zerowin_cond = _cond(
            force_fg=False, force_wincap=False,
            reel_base="BR0", reel_free="FR0",
        )
        wincap_cond = _cond(
            force_fg=True, force_wincap=True,
            reel_base="BR0", reel_free="FR0",
        )
        wincap_cond["scatter_triggers"] = {3: 1}
        wincap_cond["wild_mult_values"][self.freegame_type] = {
            2: 150, 3: 60, 5: 30, 10: 15, 20: 8, 50: 3, 100: 2
        }

        # ── Bonus mode conditions ──────────────────────────────────
        bonus_cond = {
            **freegame_cond,
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 1},
        }
        super_bonus_cond = {
            **freegame_cond,
            "reel_weights": {
                self.basegame_type: {"BR0": 1},
                self.freegame_type: {"FR0": 1},
            },
            "scatter_triggers": {3: 1},
            "pre_placed_wilds": 1,
        }

        # ── Bet Modes ─────────────────────────────────────────────
        maxwins = {
            "base": 10000, "bonus": 10000, "super_bonus": 10000,
        }

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
                    Distribution(criteria="wincap",    quota=0.001,  win_criteria=maxwins["base"],  conditions=wincap_cond),
                    Distribution(criteria="freegame",  quota=0.10,   conditions=freegame_cond),
                    Distribution(criteria="0",         quota=0.40,   win_criteria=0.0,              conditions=zerowin_cond),
                    Distribution(criteria="basegame",  quota=0.489,  conditions=basegame_cond),
                ],
            ),
            BetMode(
                name="bonus",
                cost=150.0,
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
                cost=300.0,
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
