"""游戏专用簇群识别和 Wild 单一归属算法。"""

from dataclasses import dataclass

from src.calculations.cluster import Cluster
from src.executables.executables import Executables


@dataclass(frozen=True)
class ClusterCandidate:
    symbol: str
    positions: frozenset[tuple[int, int]]
    wild_positions: frozenset[tuple[int, int]]
    payout: float

    @property
    def size(self) -> int:
        return len(self.positions)


class GameCalculations(Executables):
    """覆盖 SDK 默认簇群实现，确保 Wild 不会在同一步重复计奖。"""

    @staticmethod
    def _neighbours(board, reel: int, row: int):
        if reel > 0:
            yield reel - 1, row
        if reel + 1 < len(board):
            yield reel + 1, row
        if row > 0:
            yield reel, row - 1
        if row + 1 < len(board[reel]):
            yield reel, row + 1

    def _candidate_clusters(self) -> list[ClusterCandidate]:
        candidates = []
        wild_names = set(self.config.special_symbols["wild"])
        soul_positions = set(getattr(self, "soul_positions", set()))

        for symbol in self.config.symbol_rank:
            eligible = {
                (reel, row)
                for reel in range(self.config.num_reels)
                for row in range(self.config.num_rows[reel])
                if (
                    self.board[reel][row].name == symbol
                    or self.board[reel][row].name in wild_names
                    or (reel, row) in soul_positions
                )
            }
            visited = set()
            for start in sorted(eligible):
                if start in visited:
                    continue
                stack = [start]
                component = set()
                has_base_symbol = False
                while stack:
                    position = stack.pop()
                    if position in visited:
                        continue
                    visited.add(position)
                    component.add(position)
                    reel, row = position
                    has_base_symbol = has_base_symbol or (
                        self.board[reel][row].name == symbol
                        and self.board[reel][row].name not in wild_names
                    )
                    stack.extend(
                        neighbour
                        for neighbour in self._neighbours(self.board, reel, row)
                        if neighbour in eligible and neighbour not in visited
                    )

                paytable_key = (len(component), symbol)
                if has_base_symbol and paytable_key in self.config.paytable:
                    wild_positions = frozenset(
                        position
                        for position in component
                        if (
                            self.board[position[0]][position[1]].name in wild_names
                            or position in soul_positions
                        )
                    )
                    candidates.append(
                        ClusterCandidate(
                            symbol=symbol,
                            positions=frozenset(component),
                            wild_positions=wild_positions,
                            payout=self.config.paytable[paytable_key],
                        )
                    )

        symbol_rank = {symbol: rank for rank, symbol in enumerate(self.config.symbol_rank)}
        candidates.sort(
            key=lambda candidate: (
                -candidate.payout,
                symbol_rank[candidate.symbol],
                -candidate.size,
                min(candidate.positions),
            )
        )
        return candidates

    @staticmethod
    def _select_clusters(candidates: list[ClusterCandidate]) -> list[ClusterCandidate]:
        uncontested = [candidate for candidate in candidates if not candidate.wild_positions]
        contested = [candidate for candidate in candidates if candidate.wild_positions]
        wild_positions = sorted(
            {
                position
                for candidate in contested
                for position in candidate.wild_positions
            }
        )
        wild_bits = {position: 1 << index for index, position in enumerate(wild_positions)}
        candidate_masks = [
            sum(wild_bits[position] for position in candidate.wild_positions)
            for candidate in contested
        ]
        memo = {}

        def solve(index: int, used_mask: int):
            key = (index, used_mask)
            if key in memo:
                return memo[key]
            if index == len(contested):
                result = (0.0, ())
            else:
                skip_total, skip_selection = solve(index + 1, used_mask)
                mask = candidate_masks[index]
                if mask & used_mask:
                    result = (skip_total, skip_selection)
                else:
                    child_total, child_selection = solve(index + 1, used_mask | mask)
                    include_total = contested[index].payout + child_total
                    # 旧算法先遍历“选择”分支，并只在严格更高时覆盖；
                    # 因此同分时保留更早候选，确保历史结果完全一致。
                    if include_total >= skip_total:
                        result = (include_total, (index,) + child_selection)
                    else:
                        result = (skip_total, skip_selection)
            memo[key] = result
            return result

        _, selected_indexes = solve(0, 0)
        selected = uncontested + [contested[index] for index in selected_indexes]
        priority = {candidate: index for index, candidate in enumerate(candidates)}
        return sorted(selected, key=lambda candidate: priority[candidate])

    def evaluate_sanguo_clusters(self):
        selected = self._select_clusters(self._candidate_clusters())
        return_data = {"totalWin": 0.0, "wins": []}
        soul_positions = set(getattr(self, "soul_positions", set()))
        self.soul_consumed = False
        self.soul_winning_symbols = set()

        for candidate in selected:
            positions = sorted(candidate.positions)
            json_positions = [{"reel": reel, "row": row} for reel, row in positions]
            json_wild_positions = [
                {"reel": reel, "row": row} for reel, row in sorted(candidate.wild_positions)
            ]
            overlay_reel, overlay_row = Cluster.get_central_cluster_position(json_positions)
            contains_mega = any(
                group["positions"].issubset(candidate.positions)
                for group in getattr(self, "mega_groups", [])
            )
            mega_multiplier = self.config.mega_multiplier if contains_mega else 1
            contains_soul = bool(candidate.positions.intersection(soul_positions))
            soul_multiplier = (
                getattr(self, "soul_multiplier", 1) if contains_soul else 1
            )
            base_payout = candidate.payout * self.global_multiplier
            payout_before_soul = base_payout * mega_multiplier
            payout = payout_before_soul * soul_multiplier
            return_data["totalWin"] += payout
            if hasattr(self, "rtp_components"):
                self.rtp_components[self.current_win_source] += base_payout
                if contains_mega:
                    self.rtp_components["mega"] += payout_before_soul - base_payout
                if contains_soul:
                    self.rtp_components["soulMultiplier"] += payout - payout_before_soul
            if contains_soul:
                self.soul_consumed = True
                self.soul_winning_symbols.add(candidate.symbol)
            return_data["wins"].append(
                {
                    "symbol": candidate.symbol,
                    "clusterSize": candidate.size,
                    "win": payout,
                    "positions": json_positions,
                    "meta": {
                        "globalMult": self.global_multiplier,
                        "clusterMult": 1,
                        "winWithoutMult": candidate.payout,
                        "wildPositions": json_wild_positions,
                        "megaMultiplier": mega_multiplier,
                        "soulMultiplier": soul_multiplier,
                        "soulPositions": [
                            {"reel": reel, "row": row}
                            for reel, row in sorted(
                                candidate.positions.intersection(soul_positions)
                            )
                        ],
                        "megaGroups": [
                            [
                                {"reel": reel, "row": row}
                                for reel, row in sorted(group["positions"])
                            ]
                            for group in getattr(self, "mega_groups", [])
                            if group["positions"].issubset(candidate.positions)
                        ],
                        "ownershipAlgorithm": self.config.ownership_algorithm_version,
                        "overlay": {"reel": overlay_reel, "row": overlay_row},
                    },
                }
            )
            for reel, row in positions:
                self.board[reel][row].explode = True

        return_data["totalWin"] = round(return_data["totalWin"], 10)
        return self.board, return_data
