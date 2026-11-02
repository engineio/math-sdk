"""Generate Fracture: Gods Divided reel strips (BR0 base, FR0 free).
Deterministic (seeded). 5 reels (columns). SC only on reels 0/2/4. Mirrors
Sugar Stack density: lows common, premiums rare, wilds sparse (richer in FR0).
RTP is tuned later by the optimizer; these are sane starting strips.
Run: python3 _gen_reels.py
"""
import csv, random, os

random.seed(73)
HERE = os.path.dirname(os.path.abspath(__file__))

# per-cell weights; SC handled separately (reels 0/2/4 only)
BASE_W = {"J":17,"Q":16,"K":16,"A":15,"trident":7,"bolt":6,"poseidon":4,"zeus":3,"W":1}
FREE_W = {"J":12,"Q":12,"K":11,"A":11,"trident":8,"bolt":8,"poseidon":6,"zeus":5,"W":7}
SC_REELS = {0, 2, 4}

def build(weights, rows, sc_per_scatter_reel):
    syms = list(weights.keys()); wts = list(weights.values())
    cols = [[] for _ in range(5)]
    for r in range(5):
        col = random.choices(syms, weights=wts, k=rows)
        if r in SC_REELS:
            # sprinkle SC at non-adjacent positions
            slots = list(range(rows)); random.shuffle(slots)
            placed = []
            for s in slots:
                if len(placed) >= sc_per_scatter_reel: break
                if all(abs(s-p) > 2 for p in placed):
                    col[s] = "SC"; placed.append(s)
        cols[r] = col
    # transpose to rows of 5
    return [[cols[r][i] for r in range(5)] for i in range(rows)]

def write(name, grid):
    with open(os.path.join(HERE, name), "w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(grid)
    print(f"wrote {name}: {len(grid)} rows x 5 reels")

write("BR0.csv", build(BASE_W, 100, 3))
write("FR0.csv", build(FREE_W, 72, 3))
