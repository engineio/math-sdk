"""SUGAR STACK — Optimization parameters."""

from optimization_program.optimization_config import (
    ConstructScaling,
    ConstructParameters,
    ConstructConditions,
    verify_optimization_input,
)


class OptimizationSetup:
    """Optimization parameters for each SUGAR STACK bet mode."""

    def __init__(self, game_config):
        self.game_config = game_config
        wincaps = {bm.get_name(): bm.get_wincap() for bm in game_config.bet_modes}

        self.game_config.opt_params = {
            "base": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.01, av_win=wincaps["base"], search_conditions=wincaps["base"]
                    ).return_dict(),
                    "0": ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict(),
                    "freegame": ConstructConditions(
                        rtp=0.40, hr=50, search_conditions={"kind": "scatter"}
                    ).return_dict(),
                    "basegame": ConstructConditions(hr=3.5, rtp=0.55).return_dict(),
                },
                "scaling": ConstructScaling([
                    {"criteria": "basegame", "scale_factor": 1.2,  "win_range": (1,    5),    "probability": 1.0},
                    {"criteria": "basegame", "scale_factor": 1.5,  "win_range": (10,   30),   "probability": 1.0},
                    {"criteria": "freegame", "scale_factor": 0.8,  "win_range": (500,  1000), "probability": 1.0},
                    {"criteria": "freegame", "scale_factor": 1.2,  "win_range": (2000, 5000), "probability": 1.0},
                ]).return_dict(),
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
                ).return_dict(),
            },
            "bonus": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.01, av_win=wincaps["bonus"], search_conditions=wincaps["bonus"]
                    ).return_dict(),
                    "freegame": ConstructConditions(rtp=0.95, hr="x").return_dict(),
                },
                "scaling": ConstructScaling([
                    {"criteria": "freegame", "scale_factor": 0.9,  "win_range": (10,   50),   "probability": 1.0},
                    {"criteria": "freegame", "scale_factor": 0.8,  "win_range": (500,  2000),  "probability": 1.0},
                    {"criteria": "freegame", "scale_factor": 1.2,  "win_range": (3000, 7000),  "probability": 1.0},
                ]).return_dict(),
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
                ).return_dict(),
            },
            "super_bonus": {
                "conditions": {
                    "wincap": ConstructConditions(
                        rtp=0.01, av_win=wincaps["super_bonus"], search_conditions=wincaps["super_bonus"]
                    ).return_dict(),
                    "freegame": ConstructConditions(rtp=0.95, hr="x").return_dict(),
                },
                "scaling": ConstructScaling([
                    {"criteria": "freegame", "scale_factor": 0.8,  "win_range": (100,  500),   "probability": 1.0},
                    {"criteria": "freegame", "scale_factor": 1.3,  "win_range": (5000, 10000), "probability": 1.0},
                ]).return_dict(),
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
                ).return_dict(),
            },
        }

        verify_optimization_input(self.game_config, self.game_config.opt_params)
