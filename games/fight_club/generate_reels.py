"""Fight Club — Reel strip generator for 6x5 cascade cluster game."""

import csv
import os
import random

# Symbols per reel for base game (BR0)
# 6 reels, each with ~200 positions
# Low pay symbols appear more frequently, premiums less
# W (wild) rare, S (scatter) on specific reels only

BASE_WEIGHTS = {
    "H1": 4,   # Bull (rarest premium)
    "H2": 5,   # Viper
    "H3": 7,   # Iron Jaw
    "H4": 9,   # Ghost
    "H5": 11,  # Rookie (most common premium)
    "L1": 14,  # Brass Knuckles
    "L2": 16,  # Boxing Gloves
    "L3": 18,  # Mouthguard
    "L4": 20,  # Tape Roll
    "L5": 22,  # Towel (most common)
    "W": 3,    # Wild
    "S": 2,    # Scatter
}

# Free game weights: more wilds, no scatters (triggered separately)
FREE_WEIGHTS = {
    "H1": 5,
    "H2": 6,
    "H3": 8,
    "H4": 10,
    "H5": 12,
    "L1": 14,
    "L2": 16,
    "L3": 17,
    "L4": 18,
    "L5": 20,
    "W": 5,
    "S": 0,
}

# Wincap reels: very high wild frequency for forced max wins
WCAP_WEIGHTS = {
    "H1": 8,
    "H2": 8,
    "H3": 8,
    "H4": 6,
    "H5": 6,
    "L1": 5,
    "L2": 5,
    "L3": 4,
    "L4": 4,
    "L5": 4,
    "W": 15,
    "S": 2,
}

NUM_REELS = 6
REEL_LENGTH = 200
WCAP_LENGTH = 150


def build_weighted_pool(weights):
    """Create a flat list of symbols based on weights."""
    pool = []
    for sym, count in weights.items():
        if count > 0:
            pool.extend([sym] * count)
    return pool


def generate_reel(pool, length):
    """Generate a single reel strip, shuffled to avoid 3+ consecutive same symbols."""
    reel = []
    for _ in range(length):
        reel.append(random.choice(pool))

    # Shuffle to break up runs of 3+ same symbol
    max_passes = 5
    for _ in range(max_passes):
        changed = False
        for i in range(2, len(reel)):
            if reel[i] == reel[i-1] == reel[i-2]:
                # Swap with a random position that won't create another run
                candidates = [j for j in range(len(reel)) if j != i and j != i-1 and j != i-2]
                if candidates:
                    swap_idx = random.choice(candidates)
                    reel[i], reel[swap_idx] = reel[swap_idx], reel[i]
                    changed = True
        if not changed:
            break

    return reel


def write_csv(filename, reels_data):
    """Write reel strips to CSV. Each column = one reel."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        num_rows = len(reels_data[0])
        for row_idx in range(num_rows):
            row = [reels_data[reel][row_idx] for reel in range(len(reels_data))]
            writer.writerow(row)


def main():
    random.seed(42)  # Reproducible

    reels_dir = os.path.join(os.path.dirname(__file__), "reels")
    os.makedirs(reels_dir, exist_ok=True)

    # BR0 — Base game reels
    base_pool = build_weighted_pool(BASE_WEIGHTS)
    br0 = [generate_reel(base_pool, REEL_LENGTH) for _ in range(NUM_REELS)]
    write_csv(os.path.join(reels_dir, "BR0.csv"), br0)
    print(f"BR0.csv: {NUM_REELS} reels x {REEL_LENGTH} rows")

    # FR0 — Free game reels
    free_pool = build_weighted_pool(FREE_WEIGHTS)
    fr0 = [generate_reel(free_pool, REEL_LENGTH) for _ in range(NUM_REELS)]
    write_csv(os.path.join(reels_dir, "FR0.csv"), fr0)
    print(f"FR0.csv: {NUM_REELS} reels x {REEL_LENGTH} rows")

    # WCAP — Wincap reels
    wcap_pool = build_weighted_pool(WCAP_WEIGHTS)
    wcap = [generate_reel(wcap_pool, WCAP_LENGTH) for _ in range(NUM_REELS)]
    write_csv(os.path.join(reels_dir, "WCAP.csv"), wcap)
    print(f"WCAP.csv: {NUM_REELS} reels x {WCAP_LENGTH} rows")

    print("Done! Reel strips generated in reels/")


if __name__ == "__main__":
    main()
