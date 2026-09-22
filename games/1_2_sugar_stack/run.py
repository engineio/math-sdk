"""SUGAR STACK — Main simulation entry point."""

import os
import sys

_game_dir = os.path.dirname(os.path.abspath(__file__))
_sdk_root  = os.path.dirname(os.path.dirname(_game_dir))
for _p in [
    os.path.join(_sdk_root, "env", "src", "stakeengine"),
    _game_dir,
]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads    = 4
    rust_threads   = 16
    batching_size  = 5000
    compression    = True
    profiling      = False

    num_sim_args = {
        "base":         10000,
        "bonus":        10000,
        "super_bonus":  10000,
    }

    run_conditions = {
        "run_sims":          True,
        "run_optimization":  True,
        "run_analysis":      False,
        "run_format_checks": False,
    }

    target_modes = list(num_sim_args.keys())

    config    = GameConfig()
    gamestate = GameState(config)

    if run_conditions["run_optimization"]:
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        custom_keys = [{"kind": "scatter"}]
        create_stat_sheet(gamestate, custom_keys=custom_keys)

    if run_conditions["run_format_checks"]:
        execute_all_tests(config)
