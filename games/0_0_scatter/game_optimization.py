"""Set conditions/parameters for optimization program program"""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructFenceBias,
    ConstructConditions,
    verify_optimization_input,
)


class OptimizationSetup:
    """Handle all game mode optimization parameters."""

    def __init__(self, game_config):
        self.game_config = game_config
        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(rtp=0.001, av_win=5000, search_conditions=5000).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.376, hr=200, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=3.5, rtp=0.59).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {
                            "criteria": "basegame",
                            "scale_factor": 1.2,
                            "win_range": (1, 2),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "basegame",
                            "scale_factor": 2,
                            "win_range": (2, 5),
                            "probability": 3.0,
                        },
                        {
                            "criteria": "basegame",
                            "scale_factor": 1.9,
                            "win_range": (10, 20),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "freegame",
                            "scale_factor": 0.8,
                            "win_range": (1000, 2000),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "freegame",
                            "scale_factor": 1.2,
                            "win_range": (3000, 4000),
                            "probability": 1.0,
                        },
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[50, 100, 200],
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                    max_trial_dist=15,
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame"],
                    bias_ranges=[(3.0, 5.0)],
                    bias_weights=[0.5],
                ).return_dict(),
            },
            "bonus": {
                "conditions": {
                    "wincap": ConstructConditions(rtp=0.001, av_win=5000, search_conditions=5000).return_dict(),
                    "freegame": ConstructConditions(rtp=0.966, hr="x").return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {
                            "criteria": "freegame",
                            "scale_factor": 0.5,
                            "win_range": (20, 50),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "freegame",
                            "scale_factor": 0.8,
                            "win_range": (1000, 2000),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "freegame",
                            "scale_factor": 1.2,
                            "win_range": (3000, 4000),
                            "probability": 1.0,
                        },
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                    max_trial_dist=15,
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["freegame"],
                    bias_ranges=[(90.0, 150.0)],
                    bias_weights=[0.1],
                ).return_dict(),
            },
            # Enhanced Spins (ante), cost 2.0. Condition rtp is per unit of mode cost
            # (contribution = P(fence) * avg_win / cost), so the conditions sum to the mode RTP 0.967.
            #   freegame: P = 1/50, avg win = 50 * 0.752 * 2.0 = 75.2x bet (base's feature: 200 * 0.376)
            #   basegame: P = 1/3.5, avg win = 3.5 * 0.214 * 2.0 = 1.5x bet
            #   wincap:   P = 0.001 * 2.0 / 5000 -> 1 in 2.5M
            "ante": {
                "conditions": {
                    "wincap": ConstructConditions(rtp=0.001, av_win=5000, search_conditions=5000).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.752, hr=50, search_conditions={"symbol": "scatter"}
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=3.5, rtp=0.214).return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {"criteria": "basegame", "scale_factor": 1.2, "win_range": (1, 2), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 2.0, "win_range": (2, 5), "probability": 1.0},
                        {"criteria": "basegame", "scale_factor": 1.5, "win_range": (10, 20), "probability": 1.0},
                        {
                            "criteria": "freegame",
                            "scale_factor": 0.8,
                            "win_range": (1000, 2000),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "freegame",
                            "scale_factor": 1.2,
                            "win_range": (3000, 4000),
                            "probability": 1.0,
                        },
                        # Ante-only: at cost 2.0 the RGS etl40b check sums wins >= 80x (40 x cost), which is
                        # just above the 75.2x average feature, so a top-heavy feature can push etl40b past
                        # its 0.9 limit. Weighting 40-79.9x feature wins keeps the profile close to base's.
                        # Re-check etl40b in the format checks after optimising.
                        {
                            "criteria": "freegame",
                            "scale_factor": 1.35,
                            "win_range": (40, 79.9),
                            "probability": 1.0,
                        },
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[25, 50, 100],  # base's [50, 100, 200] at the same stake, since a spin costs 2x
                    test_weights=[0.3, 0.4, 0.3],
                    score_type="rtp",
                    max_trial_dist=15,
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["basegame"],
                    bias_ranges=[(3.0, 5.0)],
                    bias_weights=[0.5],
                ).return_dict(),
            },
            # Super Free Spins buy, cost 500: the bonus's setup scaled to the price. Its raw books pay more
            # than the 200x bonus (the multiplier never resets: raw books average ~625x with a ~x14 final
            # multiplier), so the optimiser mostly trims the top end.
            "super_bonus": {
                "conditions": {
                    "wincap": ConstructConditions(rtp=0.001, av_win=5000, search_conditions=5000).return_dict(),
                    "freegame": ConstructConditions(rtp=0.966, hr="x").return_dict(),
                },
                "scaling": ConstructScaling(
                    [
                        {
                            "criteria": "freegame",
                            "scale_factor": 0.7,
                            "win_range": (200, 500),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "freegame",
                            "scale_factor": 0.8,
                            "win_range": (1000, 2000),
                            "probability": 1.0,
                        },
                        {
                            "criteria": "freegame",
                            "scale_factor": 1.2,
                            "win_range": (3000, 4000),
                            "probability": 1.0,
                        },
                    ]
                ).return_dict(),
                "parameters": ConstructParameters(
                    num_show=5000,
                    num_per_fence=10000,
                    min_m2m=4,
                    max_m2m=8,
                    pmb_rtp=1.0,
                    sim_trials=5000,
                    test_spins=[10, 20, 50],
                    test_weights=[0.6, 0.2, 0.2],
                    score_type="rtp",
                    max_trial_dist=15,
                ).return_dict(),
                "distribution_bias": ConstructFenceBias(
                    applied_criteria=["freegame"],
                    bias_ranges=[(225.0, 375.0)],
                    bias_weights=[0.1],
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
