# RIN — cluster tumble game (7x7)

game_id: 0_0_rin
working_name: RIN
win_type: cluster
grid: 7x7
wincap: 5000
rtp: 0.96

Clusters of 5 or more like-symbols are removed from the board, and symbols above on the reelstrip
fall to fill their place. Wild (W) substitutes in clusters. Scatter (S) triggers Night Shift freespins.

#### Symbol mapping (IDs unchanged from cluster sample)
H1  Rin
H2  Fox mask
H3  Lucky cat
H4  Neon 営業中
L1  canned coffee
L2  onigiri
L3  lighter
L4  magazine
W   foxfire wild
S   door chime scatter

#### Basegame
Standard tumbling cluster game with Scatter and Wild symbols.
Minimum of 4 Scatter symbols are required for Night Shift (freeSpin) triggers.
{4: 10, 5: 12, 6: 15, 7: 18, 8: 20} freespins (copied from cluster).

Rin Dash (see below): ~5% chance after reveal, ~15% chance after each winning tumble.

#### Night Shift (freegame)
Same basegame rule, except grid positions have multipliers. Grid positions start in a 'deactivated' state. Once one win occurs,
the position is 'activated' starting with a 1x multiplier - for every winning cluster, the multiplier value at that position is increased by +1 for every winning position.
A minimum of 3 scatters are required for re-triggers
{3: 5, 4: 8, 5: 10, 6: 12, 7: 15, 8: 18} extra spins (copied from cluster).

Rin Dash: at least one dash is forced after every Night Shift reveal, plus the post-tumble chance.

#### Buy-bonus
BetMode name="bonus", cost=200.
is_buybonus=True, is_feature=False — this is how the SDK actually exposes a Clocked-in buy-bonus
(src/config/constants.py ISBUYBONUSMAPPING["bonus"]=True, ISFEATUREMAPPING["bonus"]=False;
0_0_lines / 0_0_ways / 0_0_scatter / 0_0_expwilds all set bonus this way).
The cluster sample leaves is_buybonus=False; that is not used here.

#### Rin Dash
After the reveal, and again after each winning tumble, a dash may convert one full axis
(a row or a reel, line index 0-6) into wild W. Those cells stay sticky wilds for the rest
of THIS spin's tumbles only (cleared on reset_book / each new Night Shift spin).

tumble_game_board is overridden: tumble_board() cascades exploded cells from the reelstrip,
tumbleBoard is emitted, then sticky W cells are written back so the next cluster eval sees them.
Frontend should treat rinDash.positions as sticky overlays for remaining tumbles of the spin
(tumbleBoard newSymbols are the raw cascade, not the sticky rewrite).

Event contract (board indices 0-6, no padding-row offset — unlike winInfo which adds +1):

{
  "index": <n>,
  "type": "rinDash",
  "axis": "row" | "reel",
  "line": <0-6>,
  "positions": [{"reel": int, "row": int}, ...]
}

axis "row": line is the row index; positions are all 7 cells in that row.
axis "reel": line is the reel index; positions are all 7 cells in that reel.

#### How to run
From the math-sdk root (after `make setup` / venv):

    python3 games/0_0_rin/run.py
    make run GAME=0_0_rin

run.py defaults to num_sim_args of 10 per mode so a smoke run is possible.
Optimization / analysis / format checks are off by default; flip run_conditions and raise
num_sim_args for a full distribution pass.

#### Notes
Because of the separation between basegame and freegame types - there is an additional freespin entry check to check of the criteria requires a forced
freespin condition. Otherwise, occurences of Scatter symbols tumbling onto the board during basegame criteria may appear.
