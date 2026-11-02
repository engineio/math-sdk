"""AURA FARM — Game Configuration.

Riso-print streetwear slot on the proven expanding-sticky-wild engine:
  - Base game: seeds (W) expand into full multiplier reels; multipliers
    MULTIPLY together on multi-seed lines (engine-native).
  - HARVEST SEASON (3x golden yuzu): sticky seeds that LEVEL UP every spin
    (x2 -> x128) — the AURA FARMING signature mechanic.
  - MONSOON retrigger: +5 spins, every seed levels up instantly.
  - Buys: HARVEST (bonus, 100x) and GREENHOUSE (super_bonus, 250x,
    1 pre-planted level-2 seed).
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
        self.game_id = "aura_farm"
        self.provider_number = 1
        self.working_name = "AURA FARM"
        self.wincap = 25000.0   # MAX AURA — screenshot-worthy, fenced by the optimizer
        self.win_type = "lines"
        self.rtp = 0.9600
        try:
            self.construct_paths(self.game_id)
        except TypeError:
            self.construct_paths()

        # 5x3 grid
        self.num_reels = 5
        self.num_rows = [3] * self.num_reels

        # ── Paytable (pay x line bet for 3/4/5 of a kind, 20 lines) ──
        # W pays as the top symbol (Sensei Capy).
        self.paytable = {
            (5, "W"): 12,      (4, "W"): 4,       (3, "W"): 1,
            (5, "capy"): 12,   (4, "capy"): 4,    (3, "capy"): 1,
            (5, "fade"): 9,    (4, "fade"): 2.5,  (3, "fade"): 0.8,
            (5, "nonna"): 6,   (4, "nonna"): 1.5, (3, "nonna"): 0.5,
            (5, "plume"): 5,   (4, "plume"): 1.2, (3, "plume"): 0.4,
            (5, "A"): 2.5,     (4, "A"): 0.75,    (3, "A"): 0.25,
            (5, "K"): 2,       (4, "K"): 0.6,     (3, "K"): 0.2,
            (5, "Q"): 1.5,     (4, "Q"): 0.5,     (3, "Q"): 0.15,
            (5, "J"): 1.2,     (4, "J"): 0.4,     (3, "J"): 0.1,
        }

        # ── 20 paylines on a 5x3 grid (rows 0/1/2) ──
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
            11: [2, 1, 1, 1, 0],
            12: [1, 0, 0, 0, 1],
            13: [1, 2, 2, 2, 1],
            14: [0, 1, 0, 1, 0],
            15: [2, 1, 2, 1, 2],
            16: [1, 1, 0, 1, 1],
            17: [1, 1, 2, 1, 1],
            18: [0, 2, 0, 2, 0],
            19: [2, 0, 2, 0, 2],
            20: [0, 2, 2, 2, 0],
        }

        self.include_padding = True

        # W = aura seed (wild + multiplier), SC = golden yuzu (reels 0/2/4 only)
        self.special_symbols = {
            "wild":       ["W"],
            "multiplier": ["W"],
            "scatter":    ["SC"],
        }

        # 3 SC -> 10 free spins (HARVEST SEASON); MONSOON retrigger handled in gamestate
        self.freespin_triggers = {
            self.basegame_type: {3: 10},
            self.freegame_type: {3: 10},
        }
        self.anticipation_triggers = {
            self.basegame_type: 2,
            self.freegame_type: 2,
        }

        # ── Reels ──
        reel_files = {"BR0": "BR0.csv", "FR0": "FR0.csv", "FRW": "FRW.csv"}
        self.reels = {}
        for name, filename in reel_files.items():
            self.reels[name] = self.read_reels_csv(os.path.join(self.reels_path, filename))

        self.padding_reels = {
            self.basegame_type: self.reels["BR0"],
            self.freegame_type: self.reels["FR0"],
        }

        # ── Seed landing multiplier pools (powers of 2 — clean aura levels) ──
        # The ESCALATION comes from farming (x2/spin in FS), not the landing roll.
        wild_mult_base = {2: 60, 4: 25, 8: 10, 16: 5}
        wild_mult_free = {2: 75, 4: 20, 8: 5}

        # ── Shared condition templates ──
        def _cond(force_fg, force_wincap, reel_base, reel_free=None):
            c = {
                "reel_weights": {self.basegame_type: {reel_base: 1}},
                "wild_mult_values": {self.basegame_type: wild_mult_base},
                "force_freegame": force_fg,
                "force_wincap":   force_wincap,
            }
            if reel_free:
                c["reel_weights"][self.freegame_type] = {reel_free: 1}
                c["wild_mult_values"][self.freegame_type] = wild_mult_free
            return c

        freegame_cond = _cond(force_fg=True, force_wincap=False, reel_base="BR0", reel_free="FR0")
        freegame_cond["scatter_triggers"] = {3: 1}

        basegame_cond = _cond(force_fg=False, force_wincap=False, reel_base="BR0", reel_free="FR0")
        zerowin_cond  = _cond(force_fg=False, force_wincap=False, reel_base="BR0", reel_free="FR0")

        # Wincap books draw free spins from the seed-rich FRW strip: regular FR0 is
        # deliberately too sparse to ever stack the board to exactly 25000x.
        wincap_cond = _cond(force_fg=True, force_wincap=True, reel_base="BR0", reel_free="FRW")
        wincap_cond["scatter_triggers"] = {3: 1}
        wincap_cond["wild_mult_values"][self.freegame_type] = {2: 40, 4: 30, 8: 20, 16: 10}

        # HARVEST buy — straight into the season
        bonus_cond = {
            **freegame_cond,
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
            "scatter_triggers": {3: 1},
        }
        # GREENHOUSE super buy — 1 pre-planted level-2 seed (a "grown" start).
        # 3 permanent full-reel seeds proved an unfenceable payout floor: full-column
        # wilds intersect EVERY payline, so their product multiplies every win from
        # spin 1 and the average blows past the 0.95x250 fence with zero low books.
        super_bonus_cond = {
            **freegame_cond,
            "reel_weights": {self.basegame_type: {"BR0": 1}, self.freegame_type: {"FR0": 1}},
            "scatter_triggers": {3: 1},
            "pre_placed_wilds": 1,
            "pre_placed_level": 2,
        }

        # ── Bet Modes (engine names; UI shows HARVEST / GREENHOUSE) ──
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
                cost=250.0,
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
