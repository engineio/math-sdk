"""Generate AURA FARM reel strips (BR0 base, FR0 free).
Deterministic (seeded). 5 reels (columns). SC (golden yuzu) only on reels 0/2/4.
Lows (talisman tags) common, farmers rare, seeds (W) sparse — richer in FR0 so
HARVEST SEASON plants faster. RTP tuned later by the optimizer.
Run: python3 _gen_reels.py
"""
import csv, random, os

random.seed(4321)
HERE = os.path.dirname(os.path.abspath(__file__))

# per-cell weights; SC handled separately (reels 0/2/4 only)
BASE_W = {"J":17,"Q":16,"K":16,"A":15,"plume":7,"nonna":6,"fade":4,"capy":3,"W":2}
# W kept sparse: seeds are STICKY + level up, so ~2 planted per 10-spin game is
# the balance point (W:6 planted ~1/spin -> board went all-wild, mean 8110x on a
# 250x buy and the optimizer found zero low books to fence with)
FREE_W = {"J":12,"Q":12,"K":11,"A":11,"plume":8,"nonna":8,"fade":6,"capy":5,"W":2}
SC_REELS = {0, 2, 4}

def build(weights, rows, sc_per_scatter_reel):
    syms = list(weights.keys()); wts = list(weights.values())
    cols = [[] for _ in range(5)]
    for r in range(5):
        col = random.choices(syms, weights=wts, k=rows)
        if r in SC_REELS:
            slots = list(range(rows)); random.shuffle(slots)
            placed = []
            for s in slots:
                if len(placed) >= sc_per_scatter_reel: break
                if all(abs(s-p) > 2 for p in placed):
                    col[s] = "SC"; placed.append(s)
        cols[r] = col
    return [[cols[r][i] for r in range(5)] for i in range(rows)]

def write(name, grid):
    with open(os.path.join(HERE, name), "w", newline="") as f:
        csv.writer(f, lineterminator="\n").writerows(grid)
    print(f"wrote {name}: {len(grid)} rows x 5 reels")

# FRW: seed-rich strip used ONLY by the forced-wincap condition — with sparse
# FR0 the ~0.1% of books that must hit exactly 25000x could never get there
# (acceptance loops forever). Regular play never draws from FRW.
WCAP_W = {"J":12,"Q":12,"K":11,"A":11,"plume":8,"nonna":8,"fade":6,"capy":5,"W":7}

write("BR0.csv", build(BASE_W, 100, 3))
write("FR0.csv", build(FREE_W, 72, 3))
write("FRW.csv", build(WCAP_W, 72, 3))
