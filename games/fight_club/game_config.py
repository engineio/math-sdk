"""Fight Club — Underground Fight Tournament Slot (Cascade Cluster Pays)"""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig(Config):
    """Singleton Fight Club game configuration class."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "fight_club"
        self.provider_number = 0
        self.working_name = "Fight Club"
        self.wincap = 15000.0
        self.win_type = "cluster"
        self.rtp = 0.9700
        self.construct_paths()

        # Game Dimensions — 6 reels x 5 rows
        self.num_reels = 6
        self.num_rows = [5] * self.num_reels

        # Cluster size tiers: 5-7, 8-10, 11-14, 15-30
        t1, t2, t3, t4 = (5, 7), (8, 10), (11, 14), (15, 30)

        # Paytable — (cluster_size_range, symbol): payout x bet
        # Premium fighters: H1=Bull, H2=Viper, H3=IronJaw, H4=Ghost, H5=Rookie
        # Low pay gear: L1=Knuckles, L2=Gloves, L3=Mouthguard, L4=Tape, L5=Towel
        pay_group = {
            # Bull — top premium
            (t1, "H1"): 2.0,
            (t2, "H1"): 5.0,
            (t3, "H1"): 20.0,
            (t4, "H1"): 50.0,
            # Viper
            (t1, "H2"): 1.5,
            (t2, "H2"): 4.0,
            (t3, "H2"): 15.0,
            (t4, "H2"): 40.0,
            # Iron Jaw
            (t1, "H3"): 1.0,
            (t2, "H3"): 3.0,
            (t3, "H3"): 10.0,
            (t4, "H3"): 30.0,
            # Ghost
            (t1, "H4"): 0.8,
            (t2, "H4"): 2.0,
            (t3, "H4"): 8.0,
            (t4, "H4"): 20.0,
            # Rookie
            (t1, "H5"): 0.5,
            (t2, "H5"): 1.5,
            (t3, "H5"): 5.0,
            (t4, "H5"): 15.0,
            # Brass Knuckles
            (t1, "L1"): 0.4,
            (t2, "L1"): 1.0,
            (t3, "L1"): 3.0,
            (t4, "L1"): 10.0,
            # Boxing Gloves
            (t1, "L2"): 0.3,
            (t2, "L2"): 0.8,
            (t3, "L2"): 2.5,
            (t4, "L2"): 8.0,
            # Mouthguard
            (t1, "L3"): 0.2,
            (t2, "L3"): 0.5,
            (t3, "L3"): 2.0,
            (t4, "L3"): 5.0,
            # Tape Roll
            (t1, "L4"): 0.15,
            (t2, "L4"): 0.4,
            (t3, "L4"): 1.5,
            (t4, "L4"): 4.0,
            # Towel
            (t1, "L5"): 0.1,
            (t2, "L5"): 0.3,
            (t3, "L5"): 1.0,
            (t4, "L5"): 3.0,
        }
        self.paytable = self.convert_range_table(pay_group)

        self.include_padding = True
        self.special_symbols = {"wild": ["W"], "scatter": ["S"]}

        # Scatter triggers: 4+ Fight Cards trigger bonus
        self.freespin_triggers = {
            self.basegame_type: {4: 8, 5: 10, 6: 12},
            self.freegame_type: {3: 3, 4: 5, 5: 8, 6: 10},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: min(self.freespin_triggers[self.freegame_type].keys()) - 1,
        }

        # KO Reels multiplier config (used by game_executables)
        self.ko_mult_increment = {
            "base": 1,
            "exhibition": 1,
            "title_fight": 1,
            "death_match": 2,
        }
        self.ko_mult_start = {
            "base": 1,
            "exhibition": 2,
            "title_fight": 1,
            "death_match": 3,
        }
        self.ko_mult_carries_over = {
            "base": False,
            "exhibition": False,
            "title_fight": True,
            "death_match": True,
        }

        self.maximum_board_mult = 512

        # Fighter symbols for Death Match random fighter->WILD
        self.fighter_symbols = ["H1", "H2", "H3", "H4", "H5"]

        # Reel strips
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv", "WCAP": "WCAP.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        mode_maxwins = {
            "base": 15000,
            "exhibition": 15000,
            "title_fight": 15000,
            "death_match": 15000,
        }

        self.bet_modes = [
            # BASE MODE — standard play
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
                            "scatter_triggers": {4: 1, 5: 2},
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
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
            # EXHIBITION MATCH — 75x buy, 8 FS, KO starts at 2x, resets each spin
            BetMode(
                name="exhibition",
                cost=75.0,
                rtp=self.rtp,
                max_win=mode_maxwins["exhibition"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["exhibition"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "scatter_triggers": {4: 1, 5: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                            "freespin_override": 8,
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
                            "scatter_triggers": {4: 5, 5: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                            "freespin_override": 8,
                        },
                    ),
                ],
            ),
            # TITLE FIGHT — 150x buy, 10 FS, KO starts at 1x, carries over
            BetMode(
                name="title_fight",
                cost=150.0,
                rtp=self.rtp,
                max_win=mode_maxwins["title_fight"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["title_fight"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "scatter_triggers": {4: 1, 5: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                            "freespin_override": 10,
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
                            "scatter_triggers": {4: 5, 5: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                            "freespin_override": 10,
                        },
                    ),
                ],
            ),
            # DEATH MATCH — 300x buy, 5 FS, KO starts at 3x, +2x per cascade, fighter->WILD
            BetMode(
                name="death_match",
                cost=300.0,
                rtp=self.rtp,
                max_win=mode_maxwins["death_match"],
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=mode_maxwins["death_match"],
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1, "WCAP": 5},
                            },
                            "scatter_triggers": {4: 1, 5: 2},
                            "force_wincap": True,
                            "force_freegame": True,
                            "freespin_override": 5,
                            "death_match": True,
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
                            "scatter_triggers": {4: 5, 5: 1},
                            "force_wincap": False,
                            "force_freegame": True,
                            "freespin_override": 5,
                            "death_match": True,
                        },
                    ),
                ],
            ),
        ]
