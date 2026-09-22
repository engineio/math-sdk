"""Generate reel strip CSV files for SHOGUN."""

import os
import random


# Symbols: dragon, samurai, geisha, oni, A, K, Q, J, 10, W (wild), SC (scatter)
# SC only on reels 0, 2, 4

def make_paying_symbols(
    dragon=3, samurai=4, geisha=5, oni=6,
    A=8, K=8, Q=9, J=8, ten=8,
):
    """Create the list of paying symbols for a single reel strip."""
    syms = []
    syms += ["dragon"] * dragon
    syms += ["samurai"] * samurai
    syms += ["geisha"] * geisha
    syms += ["oni"] * oni
    syms += ["A"] * A
    syms += ["K"] * K
    syms += ["Q"] * Q
    syms += ["J"] * J
    syms += ["10"] * ten
    return syms


def interleave_symbols(symbols, seed=42):
    """Shuffle symbols but prevent runs of 3+ identical symbols."""
    random.seed(seed)
    shuffled = symbols[:]
    random.shuffle(shuffled)

    # Reduce long runs: swap offending symbols with later positions
    for attempt in range(5):
        changed = False
        for i in range(2, len(shuffled)):
            if shuffled[i] == shuffled[i - 1] == shuffled[i - 2]:
                for j in range(i + 1, len(shuffled)):
                    if shuffled[j] != shuffled[i]:
                        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
                        changed = True
                        break
        if not changed:
            break
    return shuffled


def insert_symbol(symbols, sym_name, count=1, seed=42):
    """Insert symbol(s) at pseudo-random positions."""
    random.seed(seed + 99)
    for _ in range(count):
        pos = random.randint(0, len(symbols))
        symbols.insert(pos, sym_name)
    return symbols


def generate_base_reels(path, length=628, seed_base=100):
    """
    Base game reels (BR0) — matches reference 0_0_expwilds (~628 rows):
    - 4 W (wild) per reel (~0.64% wild frequency)
    - 2 SC (scatter) per scatter reel (reels 0, 2, 4)
    """
    reels = []
    scatter_reels = {0, 2, 4}
    wild_count = 4

    for i in range(5):
        syms = make_paying_symbols()  # 59 symbols
        scatter_count = 2 if i in scatter_reels else 0
        specials = wild_count + scatter_count
        needed = length - len(syms) - specials
        # Pad with mixed low-pays to fill the strip
        extras = (["A", "K", "Q", "J", "10"] * (needed // 5 + 2))[:needed]
        syms += extras

        syms = interleave_symbols(syms, seed=seed_base + i * 17)

        # Insert wilds
        syms = insert_symbol(syms, "W", count=wild_count, seed=seed_base + i * 17)

        # Insert scatters on reels 0, 2, 4
        if i in scatter_reels:
            syms = insert_symbol(syms, "SC", count=scatter_count, seed=seed_base + i * 17 + 50)

        # Trim or pad to exact length
        syms = syms[:length]
        while len(syms) < length:
            syms.append("Q")

        assert len(syms) == length, f"Reel {i} length {len(syms)} != {length}"
        reels.append(syms)

    _write_csv(path, "BR0.csv", reels, length)


def generate_freegame_reels(path, length=620, seed_base=500):
    """
    Free game reels (FR0) — matches reference 0_0_expwilds (~620 rows):
    - No SC (scatters)
    - 3 W (wild) per reel (~0.48% wild freq, ~10% chance per reel per spin)
    - Wilds that land expand to fill the whole reel and become sticky
    """
    reels = []
    wild_count = 3  # 3 wilds per reel on 620 symbols
    for i in range(5):
        syms = make_paying_symbols(
            dragon=3, samurai=4, geisha=5, oni=6,
            A=8, K=8, Q=9, J=8, ten=8,
        )  # 59 symbols

        needed = length - len(syms) - wild_count
        extras = (["A", "K", "Q", "J", "10"] * (needed // 5 + 2))[:needed]
        syms += extras

        syms = interleave_symbols(syms, seed=seed_base + i * 23)

        # Insert 3 wilds per reel
        syms = insert_symbol(syms, "W", count=wild_count, seed=seed_base + i * 23)

        syms = syms[:length]
        while len(syms) < length:
            syms.append("J")

        assert len(syms) == length, f"FR reel {i} length {len(syms)} != {length}"
        reels.append(syms)

    _write_csv(path, "FR0.csv", reels, length)


def _write_csv(path, filename, reels, length):
    num_reels = len(reels)
    filepath = os.path.join(path, filename)
    with open(filepath, "w") as f:
        for row in range(length):
            line = ",".join(reels[col][row] for col in range(num_reels))
            f.write(line + "\n")
    print(f"  Generated {filepath} ({length} rows x {num_reels} reels)")


def generate_all(reels_dir):
    os.makedirs(reels_dir, exist_ok=True)
    generate_base_reels(reels_dir)
    generate_freegame_reels(reels_dir)
    print("Reel generation complete.")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generate_all(os.path.join(script_dir, "reels"))
