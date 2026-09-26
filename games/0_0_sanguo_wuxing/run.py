"""生成《三国五行传》M2c Stake Engine 数学结果。"""

import os
import shutil

from game_config import GameConfig
from gamestate import GameState
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
from utils.rgs_verification import execute_all_tests


if __name__ == "__main__":
    num_threads = int(os.getenv("SANGUO_THREADS", "1"))
    if not 1 <= num_threads <= 4:
        raise ValueError("SANGUO_THREADS 必须在 1–4 之间")
    compression = True
    profiling = False
    simulation_count = int(os.getenv("SANGUO_SIM_COUNT", "10000"))
    if simulation_count <= 0:
        raise ValueError("SANGUO_SIM_COUNT 必须大于 0")
    # 当前上游版本的多批次验证侧车会错误累计条目；候选验证固定单批次。
    batching_size = simulation_count
    requested_modes = {
        mode.strip()
        for mode in os.getenv("SANGUO_MODES", "base,bonus").split(",")
        if mode.strip()
    }
    supported_modes = {"base", "bonus"}
    unknown_modes = requested_modes - supported_modes
    if unknown_modes:
        raise ValueError(f"未知 SANGUO_MODES: {sorted(unknown_modes)}")
    num_sim_args = {
        mode: simulation_count
        for mode in ("base", "bonus")
        if mode in requested_modes
    }

    config = GameConfig()
    gamestate = GameState(config)
    create_books(
        gamestate,
        config,
        num_sim_args,
        batching_size,
        num_threads,
        compression,
        profiling,
    )
    # M2c 不运行优化器；每次将最新 LUT 发布为 `_0`，避免沿用较小样本的旧文件。
    for bet_mode in config.bet_modes:
        mode_name = bet_mode.get_name()
        shutil.copyfile(
            gamestate.output_files.lookups[mode_name]["paths"]["base_lookup"],
            gamestate.output_files.lookups[mode_name]["paths"]["optimized_lookup"],
        )
    generate_configs(gamestate)
    execute_all_tests(config)
