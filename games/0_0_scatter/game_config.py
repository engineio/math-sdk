import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    """Load all game specific parameters and elements"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "0_0_scatter"
        self.game_name = "sample_scatter"
        self.provider_numer = 0
        self.working_name = "Sample scatter pay (pay anywhere)"
        self.wincap = 5000.0
        self.win_type = "scatter"
        self.rtp = 0.967
        self.construct_paths()

        # Game Dimensions
        self.num_reels = 6
        # Optionally include variable number of rows per reel
        self.num_rows = [5] * self.num_reels
        # Board and Symbol Properties
        t1, t2, t3, t4 = (8, 8), (9, 10), (11, 13), (14, 36)
        pay_group = {
            (t1, "H1"): 3.0,
            (t2, "H1"): 7.5,
            (t3, "H1"): 15.0,
            (t4, "H1"): 60.0,
            (t1, "H2"): 2.0,
            (t2, "H2"): 5.0,
            (t3, "H2"): 10.0,
            (t4, "H2"): 40.0,
            (t1, "H3"): 1.3,
            (t2, "H3"): 3.2,
            (t3, "H3"): 7.0,
            (t4, "H3"): 30.0,
            (t1, "H4"): 1.0,
            (t2, "H4"): 2.5,
            (t3, "H4"): 6.0,
            (t4, "H4"): 20.0,
            (t1, "L1"): 0.6,
            (t2, "L1"): 1.5,
            (t3, "L1"): 4.0,
            (t4, "L1"): 10.0,
            (t1, "L2"): 0.4,
            (t2, "L2"): 1.2,
            (t3, "L2"): 3.5,
            (t4, "L2"): 8.0,
            (t1, "L3"): 0.2,
            (t2, "L3"): 0.8,
            (t3, "L3"): 2.5,
            (t4, "L3"): 5.0,
            (t1, "L4"): 0.1,
            (t2, "L4"): 0.5,
            (t3, "L4"): 1.5,
            (t4, "L4"): 4.0,
        }
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": ["M"]}

        # The base-game award is 2 free spins per Scatter (game_executables.update_freespin_amount);
        # the basegame table states it, and its smallest key sets the trigger size.
        self.freespin_triggers = {
            self.basegame_type: {
                3: 6,
                4: 8,
                5: 10,
                6: 12,
                7: 14,
                8: 16,
                9: 18,
                10: 20,
            },
            self.freegame_type: {
                2: 3,
                3: 5,
                4: 8,
                5: 12,
                6: 14,
                7: 16,
                8: 18,
                9: 20,
                10: 22,
            },
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys()) - 1,
        }
        # Reels
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "WCAP": "WCAP.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["FR0"]

        mode_maxwins = {"base": 5000, "ante": 5000, "bonus": 5000, "super_bonus": 5000}

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=mode_maxwins["base"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["base"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "mult_values": {
                                self.basegame_type: {10: 10},
                                self.freegame_type: {10: 10},
                            },
                            "scatter_triggers": {5: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.1,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {4: 5, 5: 1},
                            "mult_values": {
                                self.basegame_type: {2: 100, 3: 80, 4: 50, 5: 20, 10: 10},
                                self.freegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                            },
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.4,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "mult_values": {
                                self.basegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                                self.freegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                            },
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "mult_values": {self.basegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            # Enhanced Spins (ante): the base game at 2x cost with Free Spins triggering ~4x as often.
            # Same reels, scatter weights, multipliers and force flags as base; only the quotas and the
            # optimisation targets (game_optimization.py) differ.
            BetMode(
                name="ante",
                cost=2.0,
                rtp=self.rtp,
                max_win=mode_maxwins["ante"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["ante"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "mult_values": {
                                self.basegame_type: {10: 10},
                                self.freegame_type: {10: 10},
                            },
                            "scatter_triggers": {5: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.2,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {4: 5, 5: 1},
                            "mult_values": {
                                self.basegame_type: {2: 100, 3: 80, 4: 50, 5: 20, 10: 10},
                                self.freegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                            },
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.3,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "mult_values": {
                                self.basegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                                self.freegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                            },
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "mult_values": {self.basegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            # Free Spins buy (200x): the global multiplier restarts at x1 on every free spin,
            # as it does for Free Spins triggered in base and ante.
            BetMode(
                name="bonus",
                cost=200,
                rtp=self.rtp,
                max_win=mode_maxwins["bonus"],
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["bonus"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "mult_values": {
                                self.basegame_type: {10: 10},
                                self.freegame_type: {10: 10},
                            },
                            "scatter_triggers": {6: 1},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {4: 10, 5: 5, 6: 1},
                            "mult_values": {
                                self.basegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                                self.freegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                            },
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                ],
            ),
            # Super Free Spins buy (500x): the same feature, but the global multiplier is never reset,
            # so every tumble's +1 carries through all remaining free spins ("persistent_mult").
            BetMode(
                name="super_bonus",
                cost=500,
                rtp=self.rtp,
                max_win=mode_maxwins["super_bonus"],
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["super_bonus"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "mult_values": {
                                self.basegame_type: {10: 10},
                                self.freegame_type: {10: 10},
                            },
                            "scatter_triggers": {6: 1},
                            "persistent_mult": True,
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.999,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {4: 10, 5: 5, 6: 1},
                            "mult_values": {
                                self.basegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                                self.freegame_type: {2: 100, 4: 80, 5: 50, 7: 20, 10: 10},
                            },
                            "persistent_mult": True,
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                ],
            ),
        ]
