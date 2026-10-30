from collections import defaultdict
from abc import ABC
from typing import List, Dict
from src.calculations.board import Board
from src.calculations.symbol import Symbol
from src.config.config import Config
from src.wins.multiplier_strategy import apply_mult


class Cluster:
    """Collection of cluster-evaluation functions."""

    @staticmethod
    def get_central_cluster_position(winning_positions: List[Dict]) -> tuple:
        """Return position on screen to display win amount."""
        all_reels = []
        all_rows = []
        for pos in winning_positions:
            all_reels.append(pos["reel"])
            all_rows.append(pos["row"])

        reel_to_overlay = int(round(sum(all_reels) / len(all_rows)))
        row_to_overlay = int(round(sum(all_rows) / len(all_rows)))

        return (reel_to_overlay, row_to_overlay)

    @staticmethod
    def get_neighbours(board: list[list[Symbol]], reel: int, row: int, local_checked: set) -> list:
        """All neighbouring symbols within board range."""
        neighbours = []
        if reel > 0 and (reel - 1, row) not in local_checked:
            neighbours.append((reel - 1, row))
            local_checked.add((reel - 1, row))
        if reel < len(board) - 1 and (reel + 1, row) not in local_checked:
            neighbours.append((reel + 1, row))
            local_checked.add((reel + 1, row))
        if row > 0 and (reel, row - 1) not in local_checked:
            neighbours.append((reel, row - 1))
            local_checked.add((reel, row - 1))
        if row < len(board[reel]) - 1 and (reel, row + 1) not in local_checked:
            neighbours.append((reel, row + 1))
            local_checked.add((reel, row + 1))
        return neighbours

    @staticmethod
    def in_cluster(board: list[list[Symbol]], reel: int, row: int, og_symbol: str, wild_key: str = "wild") -> bool:
        """Checks if a symbol (including wilds) match cluster type."""
        if board[reel][row].check_attribute(wild_key) or og_symbol == board[reel][row].name:
            return True

    @staticmethod
    def check_all_neighbours(
        board: Board,
        already_checked: set,
        local_checked: set,
        potential_cluster: list,
        reel,
        row,
        og_symbol: str,
        wild_key: str = "wild",
    ):
        """Recursively check neighbours for like-symbols."""
        neighbours = Cluster.get_neighbours(board, reel, row, local_checked)
        for reel_, row_ in neighbours:
            if Cluster.in_cluster(board, reel_, row_, og_symbol, wild_key):
                potential_cluster.append((reel_, row_))
                already_checked.add((reel_, row_))
                Cluster.check_all_neighbours(
                    board,
                    already_checked,
                    local_checked,
                    potential_cluster,
                    reel_,
                    row_,
                    og_symbol,
                    wild_key,
                )

    @staticmethod
    def get_clusters(board: list[list[Symbol]], wild_key: str = "wild") -> dict:
        """Return all symbol clusters of size >= 1."""
        # Equivalent to get_neighbours()/in_cluster()/check_all_neighbours() recursion (same visiting order),
        # with symbol names and wild flags looked up once per board instead of once per neighbour check.
        names = [[sym.name for sym in reel] for reel in board]
        wilds = [[sym.check_attribute(wild_key) for sym in reel] for reel in board]
        last_reel = len(board) - 1

        def matching_neighbours(reel, row, local_checked, symbol):
            """Mark unchecked neighbours as checked and return those belonging to the cluster."""
            matches = []
            if reel > 0 and (reel - 1, row) not in local_checked:
                local_checked.add((reel - 1, row))
                if wilds[reel - 1][row] or names[reel - 1][row] == symbol:
                    matches.append((reel - 1, row))
            if reel < last_reel and (reel + 1, row) not in local_checked:
                local_checked.add((reel + 1, row))
                if wilds[reel + 1][row] or names[reel + 1][row] == symbol:
                    matches.append((reel + 1, row))
            if row > 0 and (reel, row - 1) not in local_checked:
                local_checked.add((reel, row - 1))
                if wilds[reel][row - 1] or names[reel][row - 1] == symbol:
                    matches.append((reel, row - 1))
            if row < len(board[reel]) - 1 and (reel, row + 1) not in local_checked:
                local_checked.add((reel, row + 1))
                if wilds[reel][row + 1] or names[reel][row + 1] == symbol:
                    matches.append((reel, row + 1))
            return matches

        already_checked = set()
        clusters = defaultdict(list)
        for reel, _ in enumerate(board):
            for row, _ in enumerate(board[reel]):
                if (reel, row) not in already_checked and not wilds[reel][row]:
                    potential_cluster = [(reel, row)]
                    already_checked.add((reel, row))
                    local_checked = {(reel, row)}
                    symbol = names[reel][row]
                    stack = [iter(matching_neighbours(reel, row, local_checked, symbol))]
                    while stack:
                        position = next(stack[-1], None)
                        if position is None:
                            stack.pop()
                            continue
                        potential_cluster.append(position)
                        already_checked.add(position)
                        stack.append(iter(matching_neighbours(position[0], position[1], local_checked, symbol)))
                    clusters[symbol].append(potential_cluster)

        return clusters

    @staticmethod
    def evaluate_clusters(
        config: Config,
        board: list[list[Symbol]],
        clusters: dict,
        global_multiplier: int = 1,
        multiplier_key: str = "multiplier",
        return_data: dict = {"totalWin": 0, "wins": []},
    ) -> type:
        """Determine payout amount from cluster, including symbol multiplier and global multiplier value."""
        total_win = 0
        for sym in clusters:
            for cluster in clusters[sym]:
                syms_in_cluster = len(cluster)
                if (syms_in_cluster, sym) in config.paytable:
                    cluster_mult = 0
                    for positions in cluster:
                        if board[positions[0]][positions[1]].check_attribute(multiplier_key):
                            if int(board[positions[0]][positions[1]].get_attribute(multiplier_key)) > 0:
                                cluster_mult += board[positions[0]][positions[1]].get_attribute(multiplier_key)
                    cluster_mult = max(cluster_mult, 1)
                    sym_win = config.paytable[(syms_in_cluster, sym)]
                    symwin_mult = sym_win * cluster_mult * global_multiplier
                    total_win += symwin_mult
                    json_positions = [{"reel": p[0], "row": p[1]} for p in cluster]

                    central_pos = Cluster.get_central_cluster_position(json_positions)
                    return_data["wins"] += [
                        {
                            "symbol": sym,
                            "clusterSize": syms_in_cluster,
                            "win": symwin_mult,
                            "positions": json_positions,
                            "meta": {
                                "globalMult": global_multiplier,
                                "clusterMult": cluster_mult,
                                "winWithoutMult": sym_win,
                                "overlay": {"reel": central_pos[0], "row": central_pos[1]},
                            },
                        }
                    ]

                    for positions in cluster:
                        board[positions[0]][positions[1]].explode = True

        return board, return_data, total_win

    @staticmethod
    def get_cluster_data(
        config: Config,
        board: list[list[Symbol]],
        global_multiplier: int,
        multiplier_key: str = "multiplier",
        wild_key: str = "wild",
    ) -> None:
        """Event-ready win information."""
        clusters = Cluster.get_clusters(board, wild_key)
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        board, return_data, total_win = Cluster.evaluate_clusters(
            config,
            board,
            clusters,
            global_multiplier=global_multiplier,
            multiplier_key=multiplier_key,
            return_data=return_data,
        )

        return_data["totalWin"] += total_win

        return return_data

    @staticmethod
    def record_cluster_wins(gamestate) -> None:
        """force_record win description keys."""
        for win in gamestate.win_data["wins"]:
            gamestate.record(
                {
                    "kind": win["clusterSize"],
                    "symbol": win["symbol"],
                    "mult": int(win["meta"]["globalMult"] + win["meta"]["clusterMult"]),
                    "gametype": gamestate.gametype,
                }
            )
