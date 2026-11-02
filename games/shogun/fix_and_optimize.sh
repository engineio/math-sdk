#!/bin/bash
set -e

SDK="/workspaces/math-sdk"
ENV_LIB="$SDK/env/src/stakeengine/games/1_1_shogun/library"
DEST_LIB="$SDK/games/1_1_shogun/library"

echo "=== Step 1: Copy sim output to correct location ==="
mkdir -p "$DEST_LIB"
cp -r "$ENV_LIB"/* "$DEST_LIB"/
echo "Copied library files OK"

echo "=== Step 1b: Generate correct math_config.json ==="
MCFG="$DEST_LIB/configs/math_config.json"
python3 << 'PYEOF'
import json, os

mcfg_path = os.environ.get("MCFG_PATH", "/workspaces/math-sdk/games/1_1_shogun/library/configs/math_config.json")
os.makedirs(os.path.dirname(mcfg_path), exist_ok=True)

# Sims ran with wincap=15000 (old config), so math_config must match actual data
# Wincap fence: win_range=(15000,15000), empty search, avg_win="15000"
# Zero fence: win_range=(0,0), avg_win="0"
# Freegame/basegame: win_range=(-1,-1) means no win filter
# hr="x" means auto-calculate from remaining probability
# Field types: avg_win/hr/rtp are STRINGS (Option<String>), win_range are f64

config = {
    "game_id": "1_1_shogun",
    "bet_modes": [
        {"bet_mode": "base", "cost": 1.0, "rtp": 0.97, "max_win": 15000.0},
        {"bet_mode": "buy_bonus", "cost": 150.0, "rtp": 0.97, "max_win": 15000.0},
        {"bet_mode": "super_buy_bonus", "cost": 300.0, "rtp": 0.97, "max_win": 15000.0},
    ],
    "fences": [
        {
            "bet_mode": "base",
            "fences": [
                {"name": "wincap", "rtp": "0.01", "avg_win": "15000",
                 "identity_condition": {"search": [], "win_range_start": 15000.0, "win_range_end": 15000.0, "opposite": False}},
                {"name": "0", "rtp": "0", "avg_win": "0",
                 "identity_condition": {"search": [], "win_range_start": 0.0, "win_range_end": 0.0, "opposite": False}},
                {"name": "freegame", "rtp": "0.40", "hr": "50",
                 "identity_condition": {"search": [{"name": "kind", "value": "scatter"}], "win_range_start": -1.0, "win_range_end": -1.0, "opposite": False}},
                {"name": "basegame", "rtp": "0.56", "hr": "3.5",
                 "identity_condition": {"search": [], "win_range_start": -1.0, "win_range_end": -1.0, "opposite": False}},
            ]
        },
        {
            "bet_mode": "buy_bonus",
            "fences": [
                {"name": "wincap", "rtp": "0.01", "avg_win": "15000",
                 "identity_condition": {"search": [], "win_range_start": 15000.0, "win_range_end": 15000.0, "opposite": False}},
                {"name": "freegame", "rtp": "0.96", "hr": "x",
                 "identity_condition": {"search": [], "win_range_start": -1.0, "win_range_end": -1.0, "opposite": False}},
            ]
        },
        {
            "bet_mode": "super_buy_bonus",
            "fences": [
                {"name": "wincap", "rtp": "0.01", "avg_win": "15000",
                 "identity_condition": {"search": [], "win_range_start": 15000.0, "win_range_end": 15000.0, "opposite": False}},
                {"name": "freegame", "rtp": "0.96", "hr": "x",
                 "identity_condition": {"search": [], "win_range_start": -1.0, "win_range_end": -1.0, "opposite": False}},
            ]
        },
    ],
    "dresses": [
        {
            "bet_mode": "base",
            "dresses": [
                {"fence": "basegame", "scale_factor": "1.2", "identity_condition_win_range": [1.0, 5.0], "prob": 1.0},
                {"fence": "basegame", "scale_factor": "1.5", "identity_condition_win_range": [10.0, 30.0], "prob": 1.0},
                {"fence": "freegame", "scale_factor": "0.8", "identity_condition_win_range": [500.0, 1000.0], "prob": 1.0},
                {"fence": "freegame", "scale_factor": "1.2", "identity_condition_win_range": [2000.0, 5000.0], "prob": 1.0},
            ]
        },
        {
            "bet_mode": "buy_bonus",
            "dresses": [
                {"fence": "freegame", "scale_factor": "0.9", "identity_condition_win_range": [10.0, 50.0], "prob": 1.0},
                {"fence": "freegame", "scale_factor": "0.8", "identity_condition_win_range": [500.0, 2000.0], "prob": 1.0},
                {"fence": "freegame", "scale_factor": "1.2", "identity_condition_win_range": [3000.0, 7000.0], "prob": 1.0},
            ]
        },
        {
            "bet_mode": "super_buy_bonus",
            "dresses": [
                {"fence": "freegame", "scale_factor": "0.8", "identity_condition_win_range": [100.0, 500.0], "prob": 1.0},
                {"fence": "freegame", "scale_factor": "1.3", "identity_condition_win_range": [5000.0, 10000.0], "prob": 1.0},
            ]
        },
    ],
    "bias": [
        {"bet_mode": "base", "bias": []},
        {"bet_mode": "buy_bonus", "bias": []},
        {"bet_mode": "super_buy_bonus", "bias": []},
    ],
}

with open(mcfg_path, "w") as f:
    json.dump(config, f, indent=2)
print("Generated math_config.json OK")
PYEOF

echo "=== Step 2: Source cargo ==="
. /usr/local/cargo/env

echo "=== Step 3: Run optimizer for all modes ==="
cd "$SDK/games/shogun"
python3 run_optimizer.py

echo "=== DONE ==="
