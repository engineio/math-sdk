"""Evaluates and records winds for lines games."""

from src.calculations.symbol import Symbol
from src.config.config import Config
from src.wins.multiplier_strategy import apply_mult
from src.events.events import (
    win_info_event,
    set_win_event,
    set_total_event,
)


class Lines:
    """Collection of functions to handle line-win games."""

    @staticmethod
    def line_win_info(symbol: str, kind: int, win: float, positions: list, meta_data: dict) -> dict:
        """Construct line-win event key."""
        return {
            "symbol": symbol,
            "kind": kind,
            "win": win,
            "positions": positions,
            "meta": meta_data,
        }

    @staticmethod
    def get_lines(
        board: list[list[Symbol]],
        config: Config,
        wild_key: str = "wild",
        wild_sym: str = "W",
        multiplier_method: str = "symbol",
        global_multiplier: int = 1,
    ):
        """More efficient lines calculation"""
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        # Wild status of every board position, evaluated once per board rather than once per payline position.
        wilds = [[sym.check_attribute(wild_key) for sym in reel] for reel in board]

        for line_index, line in config.paylines.items():
            first_sym = board[0][line[0]]
            finished_wild_win = False if wilds[0][line[0]] else True
            first_non_wild = first_sym if finished_wild_win else None
            potential_line = [first_sym]

            wild_matches = 0 * (finished_wild_win) + 1 * (not (finished_wild_win))
            matches = 1 * (finished_wild_win) + 0 * (not (finished_wild_win))
            base_win, wild_win = 0, 0

            for reel in range(1, len(line)):
                sym = board[reel][line[reel]]
                if finished_wild_win:
                    if sym.name == first_non_wild.name or wilds[reel][line[reel]]:
                        matches += 1
                    else:
                        break
                else:
                    if wilds[reel][line[reel]] and first_non_wild is None:
                        wild_matches += 1
                    elif first_non_wild is None:
                        first_non_wild = sym
                        matches += 1
                        finished_wild_win = True
                    else:
                        break
                potential_line.append(sym)

            if (wild_matches, wild_sym) in config.paytable:
                wild_win = config.paytable[(wild_matches, wild_sym)]
            if first_non_wild is not None:
                if (wild_matches + matches, first_non_wild.name) in config.paytable:
                    base_win = config.paytable[(wild_matches + matches, first_non_wild.name)]

            if base_win > 0 or wild_win > 0:
                if wild_win > base_win:
                    positions = [{"reel": idx, "row": line[idx]} for idx in range(0, wild_matches)]
                    line_win, applied_mult = apply_mult(
                        board,
                        multiplier_method,
                        global_multiplier=global_multiplier,
                        win_amount=wild_win,
                        positions=positions,
                    )
                    win_dict = Lines.line_win_info(
                        potential_line[0].name,
                        wild_matches,
                        line_win,
                        positions,
                        {
                            "lineIndex": line_index,
                            "multiplier": applied_mult,
                            "winWithoutMult": wild_win,
                            "globalMult": int(global_multiplier),
                            "lineMultiplier": int(applied_mult / global_multiplier),
                        },
                    )
                else:
                    positions = [{"reel": idx, "row": line[idx]} for idx in range(0, matches + wild_matches)]
                    line_win, applied_mult = apply_mult(
                        board,
                        multiplier_method,
                        global_multiplier=global_multiplier,
                        win_amount=base_win,
                        positions=positions,
                    )
                    win_dict = Lines.line_win_info(
                        first_non_wild.name,
                        matches + wild_matches,
                        line_win,
                        positions,
                        {
                            "lineIndex": line_index,
                            "multiplier": applied_mult,
                            "winWithoutMult": base_win,
                            "globalMult": int(global_multiplier),
                            "lineMultiplier": int(applied_mult / global_multiplier),
                        },
                    )

                return_data["totalWin"] += line_win
                return_data["wins"].append(win_dict)

        return return_data

    @staticmethod
    def emit_linewin_events(gamestate) -> None:
        """Transmit win events asociated with lines wins."""
        if gamestate.win_manager.spin_win > 0:
            win_info_event(gamestate)
            gamestate.evaluate_wincap()
            set_win_event(gamestate)
        set_total_event(gamestate)

    @staticmethod
    def record_lines_wins(gamestate) -> None:
        """Data for force-file."""

        def record_line(kind: int, symbol: str, mult: int, gametype: str) -> None:
            """Force file description for line-win."""
            gamestate.record({"kind": kind, "symbol": symbol, "mult": mult, "gametype": gametype})

        for win in gamestate.win_data["wins"]:
            record_line(len(win["positions"]), win["symbol"], win["meta"]["multiplier"], gamestate.gametype)
