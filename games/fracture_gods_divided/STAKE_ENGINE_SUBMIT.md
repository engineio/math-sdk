# Fracture: Gods Divided — Stake Engine submission guide

Status snapshot (updated this session):

| Piece | State |
|------|-------|
| **Math package** (`games/fracture_gods_divided/`) | ✅ authored — re-themes the **approved Sugar Stack engine** (expanding sticky multiplier-wilds + free spins + buy modes) to 5×3 / 10-line Greek gods. |
| **Reels** (`reels/BR0.csv`, `FR0.csv`) | ✅ generated (Fracture symbols; SC on reels 0/2/4; regen via `reels/_gen_reels.py`). |
| **GitHub sim workflow** (`.github/workflows/run-fracture-sim.yml`) | ✅ added (mirrors `run-sugar-stack-sim.yml`). |
| **Math generation (books + LUTs + configs)** | ⏳ runs on **GitHub Actions** (needs Rust + numpy; not run locally). |
| **RTP optimization** | ⏳ runs in the same workflow (Rust optimizer targets `rtp=0.96`). |
| **Frontend RGS port** | ⏳ NOT done — the prototype uses client RNG; Stake replays server results. This is the largest remaining task (see §4). |
| **Portal upload + submit** | ⏳ manual, your stake-engine.com account (see §5). |

---

## 1. What the math models
- **Grid:** 5 reels × 3 rows, **10 paylines**, `win_type = "lines"`, `wincap = 10000×`, target `rtp = 0.96`.
- **Symbols:** `zeus, poseidon, bolt, trident` (premium), `A K Q J` (low), `W` wild (carries ×N multiplier), `SC` scatter (reels 0/2/4).
- **Base feature ("Fracture"):** wilds expand to a full reel and take a weighted multiplier (×2…×100); multipliers on a line multiply together.
- **Free spins ("the blessing"):** 3 SC → 8 free spins, sticky expanding multiplier-wilds, retrigger on 3 more SC.
- **Bet modes (= the blessings/buys, same pattern as Sugar Stack):**
  - `base` (cost 1.0) — natural play; server decides the blessing on a scatter trigger.
  - `bonus` (cost 100×) — **Tide of Poseidon** buy (sticky mult-wild flood).
  - `super_bonus` (cost 200×) — **Zeus's Wrath** buy (pre-placed sticky wild).
- **The "choose your blessing" decision:** in Stake's deterministic model the round is fixed before you click, so the choice is implemented as **separate buy modes** + server-assignment on natural triggers (exactly how Sugar Stack does bonus/super_bonus). The prototype's pick-a-card screen becomes a buy-menu / reveal in the FE.

## 2. Generate the math (GitHub — same as Shogun/Sugar Stack)
1. Commit `games/fracture_gods_divided/` and `.github/workflows/run-fracture-sim.yml` to the stake-engine-sdk repo and push.
2. GitHub → **Actions** → **Run Fracture Gods Divided Simulation** → **Run workflow**.
3. When it finishes, download the **`fracture-gods-divided-math`** artifact. It contains:
   - `publish_files/` — the books (`books_*.jsonl.zst`) + `lookUpTable_*.csv` + index — this is the **math upload** to the RGS.
   - `configs/` — `config.json` / `config_fe.json` (frontend math config: paytable, paylines, bet modes).
4. Sanity-check the printed RTP per mode is ~0.96. If a mode is off, tune `reels/_gen_reels.py` weights and/or `game_optimization.py` win-range buckets and re-run. (First run may surface small issues since it couldn't be executed locally — Rust + numpy aren't installed here.)

## 3. Tuning levers (if RTP / volatility needs adjustment)
- `reels/_gen_reels.py` → symbol weights (premium vs low vs W density) → re-run to regen CSVs.
- `game_config.py` → `paytable`, `wild_mult_base/bonus` pools, bet-mode `distributions` quotas, `freespin_triggers`.
- `game_optimization.py` → per-mode `win_range`/`scale_factor`/`hr` targets the optimizer hits.

## 4. Frontend (the remaining build)
The approved frontends are **vanilla + Pixi.js** clients that:
- read `sessionID` + `rgs_url` from URL params,
- call the RGS: `authenticate` → `balance` → `play` (returns the round **book**) → `end-round`,
- **replay the book's event stream** (reveal → expanding-wild → line-wins → freespins → settle) instead of running any RNG.

Our Fracture prototype (`/Users/ricamax23/Desktop/fracture-gods-divided/public/index.html`) has all the rendering/animation but is **client-authoritative**. To ship it must be converted to a replay client:
1. Add an `rgs.js` module (authenticate/balance/play/end-round) — mirror `Stake-Engine/Uploads/SHOGUN_UPLOAD`.
2. Replace `startSpin()`'s client RNG with: call `/play`, receive the book, drive the existing reel/wild/win animations from the book events.
3. Map our event names to the math's event names (reveal, expandingWild/multiplier, lineWins, freeSpinTrigger, finalWin).
4. Bundle as the FE upload (see §5).

## 5. Portal upload + submit (your stake-engine.com account — cannot be automated)
1. stake-engine.com → create the game (provider, name "Fracture: Gods Divided", id `fracture_gods_divided`).
2. **Upload math:** the `publish_files/` (+ `configs/`) from the GitHub artifact.
3. **Upload frontend:** the built FE bundle (zip; `index.html` + assets at root, matching SHOGUN_UPLOAD layout).
4. Set RTP (0.96) and bet levels; map the 3 bet modes.
5. Submit for Stake review (RTP certification + their QA gate "approval" — not instant/guaranteed).

## Honest scope note
The **math package is the part that mirrors your approved games and is done** (pending the GitHub generate run). The **frontend RGS-replay port is a substantial separate build** (the analysis estimated ~1–2k LOC) and the **submission/approval is gated on your portal account + Stake's review** — none of those can be completed locally or guaranteed "day one".
