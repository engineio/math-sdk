"""Run the Rust optimizer for all SHOGUN bet modes."""

import os
import subprocess

SDK_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPT_DIR = os.path.join(SDK_ROOT, "optimization_program")
SETUP_TOML = os.path.join(OPT_DIR, "src", "setup.toml")

MODES = ["base", "buy_bonus", "super_buy_bonus"]

MODE_CONFIGS = {
    "base": {
        "test_spins": "[50, 100, 200]",
        "test_spins_weights": "[0.3, 0.4, 0.3]",
    },
    "buy_bonus": {
        "test_spins": "[10, 20, 50]",
        "test_spins_weights": "[0.6, 0.2, 0.2]",
    },
    "super_buy_bonus": {
        "test_spins": "[10, 20, 50]",
        "test_spins_weights": "[0.6, 0.2, 0.2]",
    },
}


def write_setup_toml(mode):
    cfg = MODE_CONFIGS[mode]
    content = f'''num_show_pigs = 5000
num_pigs_per_fence = 10000
min_mean_to_median = 4
max_mean_to_median = 8
pmb_rtp = 1.0
simulation_trials = 5000
test_spins = {cfg["test_spins"]}
test_spins_weights = {cfg["test_spins_weights"]}
score_type = "rtp"
max_trial_dist = 15
game_name = "1_1_shogun"
path_to_games = "../games/"
run_1000_batch = false
bet_type = "{mode}"
threads_for_fence_construction = 16
threads_for_show_construction = 16
'''
    with open(SETUP_TOML, "w") as f:
        f.write(content)


def run_mode(mode):
    write_setup_toml(mode)
    print(f"\n{'='*60}")
    print(f"Running optimizer for mode: {mode}")
    print(f"{'='*60}")

    cargo_bin = os.path.join(os.path.expanduser("~"), ".cargo", "bin")
    env = {**os.environ, "PATH": cargo_bin + os.pathsep + os.environ.get("PATH", "")}

    result = subprocess.run(
        ["cargo", "run", "--release"],
        cwd=OPT_DIR,
        env=env,
    )
    if result.returncode != 0:
        print(f"ERROR: Optimizer failed for mode {mode} (exit {result.returncode})")
        return False
    print(f"OK: {mode} optimization complete")
    return True


if __name__ == "__main__":
    for mode in MODES:
        if not run_mode(mode):
            print(f"Stopping due to error in mode: {mode}")
            break
    else:
        print("\nAll modes optimized successfully!")
