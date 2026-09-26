## Running your first game

There are several example games provided within `/games/`, showing how common slot mechanics may be implemented. As an example let's look at `games/0_0_lines/`, a 3-row, 5-reel game paying on 20 win-lines. Wins involving 3 or more like symbols will award an amount described by `GameConfig.(paytable/payines)`.


## Run-file

Simulation parameters including number of simulations, payout statistics, optimization conditions, which modes to run etc.. are all handled within `run.py`. 

Using the default settings, running:
```sh
make run GAME=0_0_lines
```
(or calling the script manually after activating your virtual-environment)
```sh
python3 games/0_0_lines/run.py 
```
will output all the files required by the RGS. All required files to publish math results are found within the `library/publish_files/` folder. Even if this math-sdk is not being used to generate math results, the *books*, *lookup-tables* and *index* file are required for publication. 


## Testing Game Outputs

To see example output files in human-readable form, lets simulate 100 results without compression in order to inspect the JSON output, we can alter the following variables within `run.py`:
```python
num_threads = 1
compression = False

num_sim_args = {
    "base": 100,
    "bonus": 100,
}

run_conditions = {
    "run_sims": True,
    "run_optimization": False,
    "run_analysis": False
}
```
When setting `num_sim_args`, we are essentially running the function `run_spin()` within `gamestate.py` 100 times, with simulation criteria being assigned within the `GameConfig()` class. We can see which criteria (basegame, 0-wins, feature games, max-wins etc..) have been applied to which simulation within the `library/lookup_tables/lookUpTableIdToCriteria_<mode>.csv` file. Here, we will not run the optimization or analysis because 100 results does not give a large enough range of results to approach large-scale statistics. We only need 1 CPU thread, so we can change this from 10 to 1 since it should only a take a second or two to run. Inspecting the output file, `library/books/books_base.jsonl` shows each simulation, identified by `id` (1-100). Each simulation-id has an `events` tag, which communicates to the front-end framework which symbols are revealed, win positions and amounts, and any of game-specific logic. Each simulation has a `payoutMultiplier` value which is the final payout amount for that round. This value directly corresponds to the value in `library/lookup_tables/lookUpTable_base.csv`. When a round-response is returned from by the RGS from the `play/` API, it is the contents of the `events` tag which is returned in the response body. 

If we look at the results for, say, simulation 58:
```json
{
    "id": 58,
    "payoutMultiplier": 10,
    "events": [
        {
            "index": 0,
            "type": "reveal",
            "board":[...],
            "paddingPositions": [...],
            "gameType": "basegame",
            "anticipation": [...]
        },
        {
            "index": 1,
            "type": "winInfo",
            "totalWin": 10,
            "wins": [
                {
                    "symbol": "L5",
                    "kind": 3,
                    "win": 10,
                    "positions": [...],
                    "meta": {}
                }
            ]
        },
        {
            "index": 2,
            "type": "setWin",
            "amount": 10,
            "winLevel": 2
        },
        {
            "index": 3,
            "type": "setTotalWin",
            "amount": 10
        },
        {
            "index": 4,
            "type": "finalWin",
            "amount": 10
        }
    ],
    "criteria": "basegame",
    "baseGameWins": 0.1,
    "freeGameWins": 0.0
}
```
This tells up what board-symbols to reveal, the winning positions on this board, the payout amount, and sets the win counters. If we now open the lookup-table file and search for simulation number 58 we see the result: `58,1,10`, matching what was given to us within the `books` file. Note that all simulations are initially given a selection weight of `1` (the second value in each CSV row). The optimization program is what sets these weights to ensure that the game-mode is balanced to a specified RTP.


## Larger simulation batches

When starting with a new game, it is suggested to start by running a small number of simulations saved in uncompressed JSON format for debugging. Once satisfied with the gamestate output, larger simulations should be run. For a production-ready game it is typically recommended to run 100k+ simulations per mode to ensure that there is a diverse range of payout multipliers to optimize over, and to significantly reduce the chances of any single player receiving the same round result more than once. We set the following parameters indicating that we want to use 20 threads for simulating the game-logic for 10,000 simulations per mode, output in compressed (.json.zst) format, we will then use 20 threads when running the optimization algorithm (this will produce modified lookup-tables such as `lookUpTable_base_0.csv`).

```python
num_sim_args = {
    "base": int(1e4),
    "bonus": int(1e4),
}

run_conditions = {
    "run_sims": True,
    "run_optimization": True,
    "run_analysis": True,
    "upload_data": False,
}
```

In the terminal you should seethe game RTP printed out as each thread finishes
```shell
Thread 0 finished with 1.632 RTP. [baseGame: 0.043, freeGame: 1.588]
```
For the `bonus` mode, this is telling us that thread 0/10 finished with a total RTP of 163.2%, with 4.3% coming from the basegame (wins on the reveal of Scatter symbols), and 158.8% RTP coming from freegame wins. This is higher than our expected 97%, though we are forcing significantly more max-win simulations than will naturally be awarded, so this is okay. The optimization algorithm will adjust these weights to balance the game properly.


By setting `run_analysis: True` we are indicating that we would like to generate a PAR sheet, summarizing key game statistics and hit-rates. This program will use the `library/lookup_tables/lookUpTableSegmented_<mode>.csv` file to determine which game-types contributed to the final round wins, in conjunction with the pay-table and `library/forces/force_record_<mode>.json` files to generate frequency and average-win statistics for specific events or win combinations.


## Next steps

These outputs corresponding directly with example Storybook packages within the `web-sdk`. It is recommended to take look through this pack to see how these math events are passed and displayed on the frontend.
If you have your own game in mind you can use one of the sample games provided as a template and implement your own unique rules within the `games/<game_name>/` directory. You will likely need to specify configuration values for things like multipliers, prize-value etc.. wtihin `game_config.py`. Then any unique calculations and events should be handled within the games `game_executables/game_calculation` files. Generally speaking, reusable functions, events or calculation should like with `/src/`, which one-off game functionality belongs within that games folder `/games/<game_id>/`.
