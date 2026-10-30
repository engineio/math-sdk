"""Handles generating game-boards from reelstrips"""

import random
from typing import List
from src.state.state import GeneralGameState
from src.calculations.statistics import get_random_outcome
from src.events.events import reveal_event


class Board(GeneralGameState):
    """Handles generation of a game board and symbols"""

    def create_board_reelstrips(self) -> None:
        """Randomly selects stopping positions from a reelstrip."""
        if self.config.include_padding:
            top_symbols = []
            bottom_symbols = []
        self.refresh_special_syms()
        self.reelstrip_id = get_random_outcome(
            self.get_current_distribution_conditions()["reel_weights"][self.gametype]
        )
        self.reelstrip = self.config.reels[self.reelstrip_id]
        anticipation = [0] * self.config.num_reels
        board = [[]] * self.config.num_reels
        for i in range(self.config.num_reels):
            board[i] = [0] * self.config.num_rows[i]
        reel_positions = [random.randrange(0, len(self.reelstrip[reel])) for reel in range(self.config.num_reels)]
        padding_positions = [0] * self.config.num_reels
        first_scatter_reel = -1
        for reel in range(self.config.num_reels):
            reel_pos = reel_positions[reel]
            strip = self.reelstrip[reel]
            strip_len = len(strip)
            if self.config.include_padding:
                top_symbols.append(self.create_symbol(strip[(reel_pos - 1) % strip_len]))
                bottom_symbols.append(self.create_symbol(strip[(reel_pos + len(board[reel])) % strip_len]))
            for row in range(self.config.num_rows[reel]):
                sym_id = strip[(reel_pos + row) % strip_len]
                sym = self.create_symbol(sym_id)
                board[reel][row] = sym
                if sym.defn.special:
                    for special_symbol in self.special_syms_on_board:
                        for s in self.config.special_symbols[special_symbol]:
                            if board[reel][row].name == s:
                                self.special_syms_on_board[special_symbol] += [{"reel": reel, "row": row}]
                                if (
                                    board[reel][row].check_attribute("scatter")
                                    and len(self.special_syms_on_board[special_symbol])
                                    >= self.config.anticipation_triggers[self.gametype]
                                    and first_scatter_reel == -1
                                ):
                                    first_scatter_reel = reel + 1
            padding_positions[reel] = (reel_positions[reel] + len(board[reel]) + 1) % strip_len

        if first_scatter_reel > -1 and first_scatter_reel != self.config.num_reels:
            count = 1
            for reel in range(first_scatter_reel, self.config.num_reels):
                anticipation[reel] = count
                count += 1

        for r in range(1, self.config.num_reels):
            if anticipation[r - 1] > anticipation[r]:
                raise RuntimeError

        self.board = board
        self.get_special_symbols_on_board()
        self.reel_positions = reel_positions
        self.padding_position = padding_positions
        self.anticipation = anticipation
        if self.config.include_padding:
            self.top_symbols = top_symbols
            self.bottom_symbols = bottom_symbols

    def force_board_from_reelstrips(self, reelstrip_id: str, force_stop_positions: List[List]) -> None:
        """Creates a gameboard from specified stopping positions."""
        if self.config.include_padding:
            top_symbols = []
            bottom_symbols = []
        self.refresh_special_syms()
        self.reelstrip_id = reelstrip_id
        self.reelstrip = self.config.reels[self.reelstrip_id]
        anticipation = [0] * self.config.num_reels
        board = [[]] * self.config.num_reels
        for i in range(self.config.num_reels):
            board[i] = [0] * self.config.num_rows[i]

        reel_positions = [None] * self.config.num_reels
        for r, s in force_stop_positions.items():
            reel_positions[r] = s - random.randint(0, self.config.num_rows[r] - 1)
        for r, _ in enumerate(reel_positions):
            if reel_positions[r] is None:
                reel_positions[r] = random.randrange(0, len(self.reelstrip[r]))

        padding_positions = [0] * self.config.num_reels
        first_scatter_reel = -1
        for reel in range(self.config.num_reels):
            reel_pos = reel_positions[reel]
            if self.config.include_padding:
                top_symbols.append(
                    self.create_symbol(self.reelstrip[reel][(reel_pos - 1) % len(self.reelstrip[reel])])
                )
                bottom_symbols.append(
                    self.create_symbol(
                        self.reelstrip[reel][(reel_pos + len(board[reel])) % len(self.reelstrip[reel])]
                    )
                )
            for row in range(self.config.num_rows[reel]):
                sym_id = self.reelstrip[reel][(reel_pos + row) % len(self.reelstrip[reel])]
                sym = self.create_symbol(sym_id)
                board[reel][row] = sym

                if sym.defn.special:
                    for special_symbol in self.special_syms_on_board:
                        for s in self.config.special_symbols[special_symbol]:
                            if board[reel][row].name == s:
                                self.special_syms_on_board[special_symbol] += [{"reel": reel, "row": row}]
                                if (
                                    board[reel][row].check_attribute("scatter")
                                    and len(self.special_syms_on_board[special_symbol])
                                    >= self.config.anticipation_triggers[self.gametype]
                                    and first_scatter_reel == -1
                                ):
                                    first_scatter_reel = reel + 1
                padding_positions[reel] = (reel_positions[reel] + len(board[reel]) + 1) % len(self.reelstrip[reel])

        if first_scatter_reel > -1 and first_scatter_reel <= self.config.num_reels:
            count = 1
            for reel in range(first_scatter_reel, self.config.num_reels):
                anticipation[reel] = count
                count += 1

        self.board = board
        self.reel_positions = reel_positions
        self.padding_position = padding_positions
        self.anticipation = anticipation
        if self.config.include_padding:
            self.top_symbols = top_symbols
            self.bottom_symbols = bottom_symbols

    def create_symbol(self, name: str):
        sym = self.symbol_storage.create_symbol(name)
        if name in self.special_symbol_functions:
            for func in self.special_symbol_functions[name]:
                func(sym)

        return sym

    def refresh_special_syms(self) -> None:
        """Reset recorded speical symbols on board."""
        self.special_syms_on_board = {}
        for s in self.config.special_symbols:
            self.special_syms_on_board[s] = []

    def get_special_symbols_on_board(self) -> None:
        """Scans board for any active special symbols."""
        self.refresh_special_syms()
        for reel, _ in enumerate(self.board):
            for row, _ in enumerate(self.board[reel]):
                if self.board[reel][row].defn.special:
                    for specialType in list(self.special_syms_on_board.keys()):
                        if self.board[reel][row].check_attribute(specialType):
                            self.special_syms_on_board[specialType].append({"reel": reel, "row": row})

    def transpose_board_string(self, board_string: List[List[str]]) -> List[List[str]]:
        """Transpose symbol names in the format displayed to the player during the game."""
        return [list(row) for row in zip(*board_string)]

    def print_board(self, board: List[List[object]]) -> List[List[str]]:
        "Prints transposed symbol names to the terminal."
        string_board = []
        max_sum_length = max(len(sym.name) for row in board for sym in row) + 1
        board_string = [[sym.name.ljust(max_sum_length) for sym in reel] for reel in board]
        transpose_board = self.transpose_board_string(board_string)
        print("\n")
        for row in transpose_board:
            string_board.append("".join(row))
            print("".join(row))
        print("\n")
        return string_board

    def board_string(self, board: List[List[object]]):
        """Prints symbol names only from gamestate.board."""
        board_str = [] * self.config.num_reels
        for reel in range(len(board)):
            board_str.append([x.name for x in board[reel]])
        return board_str

    def draw_board(self, emit_event: bool = True, trigger_symbol: str = "scatter") -> None:
        """Instead of retrying to draw a board, force the initial revel to have a
        specific number of scatters, if the betmode criteria specifies this."""
        if (
            self.get_current_distribution_conditions()["force_freegame"]
            and self.gametype == self.config.basegame_type
        ):
            num_scatters = get_random_outcome(self.get_current_distribution_conditions()["scatter_triggers"])
            self.force_special_board(trigger_symbol, num_scatters)
        elif (
            not (self.get_current_distribution_conditions()["force_freegame"])
            and self.gametype == self.config.basegame_type
        ):
            self.create_board_reelstrips()
            while self.count_special_symbols(trigger_symbol) >= min(
                self.config.freespin_triggers[self.gametype].keys()
            ):
                self.create_board_reelstrips()
        else:
            self.create_board_reelstrips()
        if emit_event:
            reveal_event(self)

    def force_special_board(self, force_criteria: str, num_force_syms: int) -> None:
        """Force a board to have a specified number of symbols.
        Set a specific type of special symbol on a given number of reels.
        This function is mostly used to set the board so that there is a given number
        of scatter symbols.

        Args:
            force_criteria: The type of symbol to force on the board. (e.g. "scatter")
            num_force_syms: The number of symbols to force on the board.

        Note: If it is possible for two target symbols to appear on one reel, this method
        will not be able to guarantee an exact number of target symbols or actually random
        reel positions. I.e. Ensure the reels do not have stacked scatter symbols.
        """
        while True:
            self._force_special_board(force_criteria, num_force_syms)
            if (
                force_criteria in self.config.special_symbols
                and self.count_special_symbols(force_criteria) == num_force_syms
            ):
                break
            elif (
                not (force_criteria in self.config.special_symbols)
                and self.count_symbols_on_board(force_criteria) == num_force_syms
            ):
                break

    def _force_special_board(self, force_criteria: str, num_force_syms: int) -> None:
        """
        Helper function for forcing special (or name specific) symbols
        """
        reelstrip_id = get_random_outcome(
            self.get_current_distribution_conditions()["reel_weights"][self.gametype]
        )
        reelstops = self.get_syms_on_reel(reelstrip_id, force_criteria)

        sym_prob = []
        for x in range(self.config.num_reels):
            sym_prob.append(len(reelstops[x]) / len(self.config.reels[reelstrip_id][x]))
        force_stop_positions = {}
        possible_reels = [i for i in range(self.config.num_reels) if sym_prob[i] > 0]
        possible_probs = [p for p in sym_prob if p > 0]

        while len(force_stop_positions) != num_force_syms and len(possible_reels) > 0:
            chosen_reel = random.choices(possible_reels, possible_probs)[0]
            chosen_stop = random.choice(reelstops[chosen_reel])
            sym_prob[chosen_reel] = 0
            force_stop_positions[int(chosen_reel)] = int(chosen_stop)
            possible_reels = [i for i in range(self.config.num_reels) if sym_prob[i] > 0]
            possible_probs = [p for p in sym_prob if p > 0]

        force_stop_positions = dict(sorted(force_stop_positions.items(), key=lambda x: x[0]))
        self.force_board_from_reelstrips(reelstrip_id, force_stop_positions)

    def get_syms_on_reel(self, reel_id: str, target_symbol: str) -> List[List]:
        """Return reelstop positions for a specific symbol name."""
        reel = self.config.reels[reel_id]
        # Reelstrips are static, so cache the scan; it is recomputed if the reelstrip object is replaced.
        cache = self._syms_on_reel_cache
        cached = cache.get((reel_id, target_symbol))
        if cached is not None and cached[0] is reel:
            return [list(positions) for positions in cached[1]]
        reelstop_positions = [[] for _ in range(self.config.num_reels)]
        for r in range(self.config.num_reels):
            for s in range(len(reel[r])):
                if (
                    target_symbol in self.config.special_symbols
                    and reel[r][s] in self.config.special_symbols[target_symbol]
                ):
                    reelstop_positions[r].append(s)
                elif reel[r][s] == target_symbol:
                    reelstop_positions[r].append(s)

        cache[(reel_id, target_symbol)] = (reel, [list(positions) for positions in reelstop_positions])
        return reelstop_positions

    def count_special_symbols(self, special_sym_criteria: str) -> int:
        "Returns integer number of active symbols of any 'special' kind."
        return len(self.special_syms_on_board[special_sym_criteria])

    def count_symbols_on_board(self, symbol_name: str) -> int:
        """Count number of sumbols on the board matching the target name."""
        symbol_count = 0
        for idx, _ in enumerate(self.board):
            for idy, _ in enumerate(self.board[idx]):
                if self.board[idx][idy].name.upper() == symbol_name.upper():
                    symbol_count += 1
        return symbol_count

    def get_symbol_positions(self, target_symbol: str) -> list:
        """Get symbol positions currently on board"""
        symbol_positions = {}
        symbol_positions[target_symbol] = []
        for idx, _ in enumerate(self.board):
            for idy, _ in enumerate(self.board[idx]):
                if self.board[idx][idy].name == target_symbol:
                    symbol_positions[target_symbol].append({"reel": idx, "row": idy})

        return symbol_positions

    def add_symbols_to_board(self, symbol_name: str, additional_count: int):
        """Add additional symbols to game board."""
        free_positions = []
        for idx, _ in enumerate(len(self.board)):
            for idy, _ in enumerate(len(self.board[idx])):
                if self.board[idx][idy].name != symbol_name:
                    free_positions.append((idx, idy))

        assert len(free_positions) >= additional_count, "not enough free place for additional symbols"

        new_positions = random.choices(free_positions, additional_count)[0]
        random.shuffle(new_positions)
        for np in new_positions:
            self.board[np[0]][np[1]] = self.create_symbol(symbol_name)
