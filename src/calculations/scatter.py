"""Handle win calculation for pay-anywhere games"""

from typing import List, Dict
from collections import defaultdict
from src.config.config import Config
from src.calculations.symbol import Symbol


class Scatter:
    """Collection of Scatter-pays functions."""

    @staticmethod
    def get_central_scatter_position(
        rows_for_overlay: List, winning_positions: List[Dict], max_reels: int, max_rows: int
    ) -> tuple:
        """Return position on screen to display win amount."""
        closest_to_middle = 100
        reel_to_overlay = 0
        row_to_overlay = 0
        for pos in winning_positions:
            reel, row = pos["reel"], pos["row"]
            dist_from_middle = (reel - max_reels / 2) ** 2 + (row - max_rows / 2) ** 2
            if (
                dist_from_middle < closest_to_middle
                and row not in rows_for_overlay
                and len(rows_for_overlay) < max_reels
            ):
                closest_to_middle = dist_from_middle
                reel_to_overlay = reel
                row_to_overlay = row

        return (reel_to_overlay, row_to_overlay)

    @staticmethod
    def get_scatterpay_wins(
        config: Config,
        board: list[list[Symbol]],
        wild_key: str = "wild",
        multiplier_key: str = "multiplier",
        global_multiplier: int = 1,
    ) -> dict:
        """Return win data for all paying symbols"""
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        rows_for_overlay = []
        symbols_on_board = defaultdict(list)
        wild_positions = []
        total_win = 0.0
        wild_names = set(config.special_symbols[wild_key])
        for reel_idx, reel in enumerate(board):
            for row_idx, symbol in enumerate(reel):
                symbol_name = symbol.name
                if symbol_name not in wild_names:
                    symbols_on_board[symbol_name].append({"reel": reel_idx, "row": row_idx})
                else:
                    wild_positions.append({"reel": reel_idx, "row": row_idx})

        # Update all symbol positions with wilds, as this symbol is shared
        for sym in symbols_on_board:
            if len(wild_positions) > 0:
                symbols_on_board[sym].extend(wild_positions)
            win_size = len(symbols_on_board[sym])
            if (win_size, sym) in config.paytable:
                symbol_mult = 0
                for p in symbols_on_board[sym]:
                    if board[p["reel"]][p["row"]].check_attribute(multiplier_key):
                        symbol_mult += board[p["reel"]][p["row"]].get_attribute(multiplier_key)

                    board[p["reel"]][p["row"]].explode = True

                symbol_mult = max(symbol_mult, 1)
                overlay_position = Scatter.get_central_scatter_position(
                    rows_for_overlay, symbols_on_board[sym], len(board), len(board[0])
                )
                rows_for_overlay.append(overlay_position[1])
                symbol_win_data = {
                    "symbol": sym,
                    "win": config.paytable[(win_size, sym)] * global_multiplier * symbol_mult,
                    "positions": symbols_on_board[sym],
                    "meta": {
                        "globalMult": global_multiplier,
                        "clusterMult": symbol_mult,
                        "winWithoutMult": config.paytable[(win_size, sym)],
                        "overlay": {
                            "reel": overlay_position[0],
                            "row": overlay_position[1],
                        },
                    },
                }
                total_win += symbol_win_data["win"]
                return_data["wins"].append(symbol_win_data)

        return_data["totalWin"] = total_win

        return return_data

    @staticmethod
    def record_scatter_wins(gamestate) -> None:
        """Force-file description key generator."""
        for win in gamestate.win_data["wins"]:
            gamestate.record(
                {
                    "kind": len(win["positions"]),
                    "symbol": win["symbol"],
                    "totalMult": int(win["meta"]["globalMult"] + win["meta"]["clusterMult"]),
                    "gametype": gamestate.gametype,
                }
            )
