"""Stake Engine 通用状态的项目级扩展。"""

from collections import defaultdict

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    def reset_book(self):
        super().reset_book()
        self.dual_wild_seen = False
        self.dual_wild_w1_positions = []
        self.dual_wild_w2_positions = []
        self.current_win_source = "natural"
        self.rtp_components = defaultdict(float)
        self.mega_groups = []
        self.return_mark_symbol = None
        self.pending_return_clusters = []
        self.feature_charge = 0
        self.feature_queue = []
        self.enqueued_features = set()
        self.executed_features = []
        self.cascade_steps = 0
        self.soul_level = 1
        self.soul_level_progress = 0
        self.soul_total_collected = 0
        self.soul_multiplier = 1
        self.soul_positions = set()
        self.soul_consumed = False
        self.soul_winning_symbols = set()

    def assign_special_sym_function(self):
        # W1/W2 的 wild 属性由 config.special_symbols 自动赋值。
        pass
