"""《三国五行传》M2c 数学原型配置。"""

import os

from src.config.betmode import BetMode
from src.config.config import Config
from src.config.distributions import Distribution


class GameConfig(Config):
    """Stake Engine Math SDK 游戏配置单例。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()

        self.game_id = "0_0_sanguo_wuxing"
        self.provider_name = "sanguo_wuxing"
        self.provider_number = 360
        self.game_name = "Sanguo Wuxing Zhuan"
        self.working_name = "三国五行传：赤壁·五行奇策"
        self.math_version = "m2d.0.0-candidate"
        self.ownership_algorithm_version = "max-total-pay-v1"
        self.rtp = 0.96
        self.wincap = 50_000.0
        self.win_type = "cluster"
        self.stream_books = True
        self.write_event_list = False
        self.construct_paths()

        self.num_reels = 7
        self.num_rows = [7] * self.num_reels
        self.include_padding = True

        tier_5 = (5, 5)
        tier_6_8 = (6, 8)
        tier_9_12 = (9, 12)
        tier_13_24 = (13, 24)
        tier_25_49 = (25, 49)
        ranges = (tier_5, tier_6_8, tier_9_12, tier_13_24, tier_25_49)
        symbol_pays = {
            "H1": (10.0, 25.0, 50.0, 120.0, 300.0),
            "H2": (6.0, 15.0, 30.0, 80.0, 200.0),
            "H3": (4.0, 10.0, 20.0, 60.0, 150.0),
            "H4": (2.6, 6.4, 14.0, 40.0, 100.0),
            "H5": (2.0, 5.0, 12.0, 30.0, 80.0),
            "L1": (1.2, 3.0, 8.0, 20.0, 50.0),
            "L2": (1.0, 2.4, 7.0, 16.0, 40.0),
            "L3": (0.8, 2.0, 6.0, 14.0, 36.0),
            "L4": (0.6, 1.6, 5.0, 12.0, 30.0),
            "L5": (0.4, 1.0, 3.0, 8.0, 20.0),
        }
        pay_group = {}
        for symbol, pays in symbol_pays.items():
            for pay_range, payout in zip(ranges, pays):
                pay_group[(pay_range, symbol)] = payout
        self.paytable = self.convert_range_table(pay_group)

        self.symbol_rank = tuple(symbol_pays)
        self.special_symbols = {
            "wild": ["W1", "W2"],
            "triggerWildW1": ["W1"],
            "triggerWildW2": ["W2"],
            # 本游戏由 W1+W2 组合触发，Scatter 类型仅用于兼容 SDK 通用接口。
            "scatter": [],
        }

        # 双 Wild 由游戏状态机直接判断。50 是不可达到的 SDK 保护阈值。
        self.freespin_triggers = {
            self.basegame_type: {50: 5},
            self.freegame_type: {50: 5},
        }
        self.anticipation_triggers = {
            self.basegame_type: 49,
            self.freegame_type: 49,
        }

        # M2b 基础功能初始参数。完整基础游戏目标 RTP 约 68%。
        self.max_cascade_steps = 100
        self.max_book_events = 1_000
        self.feature_charge_thresholds = {
            3: "wood",
            4: "fire",
            5: "metal",
            6: "water",
        }
        self.feature_execution_order = ("wood", "fire", "metal", "water", "earth")
        self.feature_round_multipliers = {0: 1, 1: 1, 2: 2, 3: 3, 4: 5, 5: 10}
        self.feature_cascades_charge_meter = False

        self.mega_merge_probability = 0.20
        self.mega_multiplier = 2
        self.rescue_trigger_probability = 0.044
        self.rescue_wild_count_weights = {1: 35, 2: 25, 3: 18, 4: 10, 5: 6, 6: 3, 7: 2, 8: 1}
        self.return_mark_probability = 0.27
        self.return_wilds_per_cluster = 2

        self.wood_wild_count_weights = {1: 35, 2: 25, 3: 18, 4: 10, 5: 6, 6: 3, 7: 2, 8: 1}
        self.fire_center = (3, 3)

        # M2c 成长武魂免费游戏。
        self.soul_initial_spins = 5
        self.soul_level_thresholds = (5, 5, 4, 4, 3, 3)
        self.soul_level_added_spins = (4, 3, 2, 2, 1, 1)
        self.soul_level_multipliers = (1, 1, 1, 1, 5, 7, 10)

        self.reels = {
            "BR0": self.read_reels_csv(os.path.join(self.reels_path, "BR0.csv")),
            "FR0": self.read_reels_csv(os.path.join(self.reels_path, "FR0.csv")),
            "FRB0": self.read_reels_csv(os.path.join(self.reels_path, "FRB0.csv")),
        }

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="basegame",
                        quota=1.0,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    )
                ],
            ),
            BetMode(
                name="bonus",
                cost=100.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=True,
                distributions=[
                    Distribution(
                        criteria="bonus",
                        quota=1.0,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FRB0": 1},
                            },
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    )
                ],
            ),
        ]
