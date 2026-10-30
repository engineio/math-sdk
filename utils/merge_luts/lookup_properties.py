"""Lookup table properties and helpful functions"""

import os
from collections import defaultdict
import numpy as np


class LookupProperties:
    """Extract lookup table characteristics"""

    def __init__(self, game_id, mode):
        self.game_id = game_id
        self.lookup_path = os.path.join("games", game_id, "library", "publish_files", f"LookUpTable_{mode}_0.csv")
        self.segment_path = os.path.join(
            "games", game_id, "library", "lookup_tables", f"LookupTableSegmented_{mode}.csv"
        )
        self.payouts = []
        self.payouts_ints = []
        self.weights_ints = []
        self.weights_norm = []
        self.segmented_array = []
        self.total_weight = 0
        self.segmented_mapping = defaultdict(str)
        self.unique_critera = list(set(self.segmented_array))
        self.criteria_mapping = defaultdict(list)
        self.win_mapping = defaultdict(list)
        self.weight_mapping = defaultdict(list)
        self.read_lookup_table()
        self.read_segmented_table()
        self.extract_criteria_indicies()

    def read_lookup_table(self):
        "read csv lookup table"
        with open(self.lookup_path, "r", encoding="utf-8") as f:
            for line in f:
                _, w, p = line.strip().split(",")
                self.payouts.append(round(int(p) / 100, 3))
                self.payouts_ints.append(int(p))
                self.weights_ints.append(int(w))
                self.total_weight += int(w)

        self.weights_norm = [w / self.total_weight for w in self.weights_ints]

    def read_segmented_table(self):
        "find criteria mapping"
        with open(self.segment_path, "r", encoding="utf-8") as f:
            for line in f:
                idx, criteria, _, _ = line.strip().split(",")
                self.segmented_mapping[int(idx)] = criteria
                self.segmented_array.append(criteria)

    def extract_criteria_indicies(self):
        "find loookup index for all unique criteria"
        for idx, entry in enumerate(self.segmented_array):
            self.criteria_mapping[entry].append(idx)
            self.win_mapping[entry].append(self.payouts[idx])
            self.weight_mapping[entry].append(self.weights_ints[idx])

    def calculate_criteria_av_win(self, target_criteria):
        "find average win conditional on the given criteria"
        subset_weights = np.array(self.weight_mapping[target_criteria])
        subset_payouts = np.array(self.win_mapping[target_criteria])
        return float(subset_payouts @ subset_weights) / self.total_weight


def calculate_new_freegame_probabilities(
    base_table: LookupProperties,
    bonus_table: LookupProperties,
    target_hr: float,
    freegame_key: str,
):
    """merge optimized bonus lookup into base"""
    fg_rtp_contribution, fg_act_hr = 0.0, 0.0
    new_base_weights = []
    fg_weight_contribution = []
    counter = 0

    total_base_weight = base_table.total_weight
    freegame_indices = set(base_table.criteria_mapping[freegame_key])
    for idx, bp in enumerate(base_table.payouts):
        if idx in freegame_indices:
            assert bp == bonus_table.win_mapping[freegame_key][counter]
            w = target_hr * (bonus_table.weight_mapping[freegame_key][counter] / bonus_table.total_weight)
            fg_rtp_contribution += bp * w
            fg_act_hr += w
            new_base_weights.append(int(total_base_weight * w))
            fg_weight_contribution.append(int(total_base_weight * w))
            counter += 1
        else:
            new_base_weights.append(base_table.weights_ints[idx])

    return new_base_weights, fg_rtp_contribution, fg_act_hr, fg_weight_contribution


def override_optimized_lookup(filename, base_payout, new_weights, sim_start=1):
    """write new lookup table weights"""
    with open(filename, "w", encoding="utf-8") as f:
        for weight, payout in zip(new_weights, base_payout):
            f.write(f"{sim_start},{weight},{payout}" + "\n")
