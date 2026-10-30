"""Given optimized bonus and base lookup tables, substitute bonus probabilities into basegame lookup
NOTE: This feature is experimental....
"""

import numpy as np
from utils.merge_luts.lookup_properties import (
    LookupProperties,
    calculate_new_freegame_probabilities,
    override_optimized_lookup,
)
from utils.merge_luts.helper_funcs import (
    compare_payouts_array,
    plot_function_shapes,
    print_solution_summary,
)


def run(game_id: str, swap_key: str, mode_cost: float, plot_overlay=False, override_table=False):
    """Main function: only valid for single key swaps from bonus->base substitutions."""
    base_table = LookupProperties(game_id, "base")
    bonus_table = LookupProperties(game_id, "bonus")

    # verify this substitution method is valid
    assert len(base_table.criteria_mapping[swap_key]) == len(
        bonus_table.criteria_mapping[swap_key]
    ), f"{swap_key} payout arrays do not match in length"
    assert compare_payouts_array(
        base_table.win_mapping[swap_key], bonus_table.win_mapping[swap_key]
    ), f"{swap_key} payout arrays must be identical"

    # find freegame contribtuion properties from base-game
    fg_wins = base_table.win_mapping[swap_key]
    fg_total = np.array(base_table.weight_mapping[swap_key]).sum()
    fg_contribution_in_base = base_table.calculate_criteria_av_win(swap_key) / mode_cost
    Efg = bonus_table.calculate_criteria_av_win("freegame")

    H = fg_contribution_in_base / Efg  # freegame trigger probability required

    new_base_weights, fg_rtp_contribution, fg_act_hr, fg_weight_contribution = (
        calculate_new_freegame_probabilities(base_table, bonus_table, H, swap_key)
    )
    new_rtp = np.dot(base_table.payouts, new_base_weights) / sum(new_base_weights)
    new_fg_total = np.array(fg_weight_contribution).sum()

    print_solution_summary(Efg, H, fg_contribution_in_base, fg_act_hr, fg_rtp_contribution, new_rtp)

    base_fg_norm = [x / fg_total for x in base_table.weight_mapping[swap_key]]
    new_fg_norm = [x / new_fg_total for x in fg_weight_contribution]
    bonus_fg_total = np.array(bonus_table.weight_mapping[swap_key]).sum()
    bonus_norm = [x / bonus_fg_total for x in bonus_table.weight_mapping[swap_key]]

    if override_table:
        file_name = f"games/{game_id}/library/publish_files/LookUpTable_base_0.csv"
        override_optimized_lookup(file_name, base_table.payouts_ints, new_base_weights)

    if plot_overlay:
        plot_function_shapes(fg_wins, base_fg_norm, new_fg_norm, bonus_norm)


if __name__ == "__main__":

    GAME_ID = "0_0_lines_feature_match"
    BASE_COST = 1.0
    FREEGAME_KEY = "freegame"

    run(GAME_ID, FREEGAME_KEY, BASE_COST, True, True)
