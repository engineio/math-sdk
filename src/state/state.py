from copy import copy, deepcopy
from abc import ABC, abstractmethod
from warnings import warn
import json
import random
import zstandard as zstd

# from src.config.config import BetMode
from src.wins.win_manager import WinManager
from src.calculations.symbol import SymbolStorage
from src.config.output_filenames import OutputFiles
from src.state.books import Book
from src.write_data.write_data import (
    print_recorded_wins,
    make_lookup_tables,
    write_json,
    make_lookup_pay_split,
    write_library_events,
)


class GeneralGameState(ABC):
    """Master gamestate which other classes inherit from."""

    def __init__(self, config):
        self.config = config
        self.output_files = OutputFiles(self.config)
        self.win_manager = WinManager(self.config.basegame_type, self.config.freegame_type, config.wincap)
        self.library = {}
        self.recorded_events = {}
        self._payout_ints = []
        self.special_symbol_functions = {}
        self.temp_wins = []
        self.create_symbol_map()
        self.assign_special_sym_function()
        self.sim = 0
        self.criteria = ""
        self.book = Book(self.sim, self.criteria)
        self.repeat = True
        self.repeat_count = 0
        self.win_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.reset_seed()
        self.reset_book()
        self.reset_fs_spin()

    def create_symbol_map(self) -> None:
        """Construct all valid symbols from config file (from pay-table and special symbols)."""
        all_symbols_list = set()
        for key, _ in self.config.paytable.items():
            all_symbols_list.add(key[1])

        for key in self.config.special_symbols:
            for sym in self.config.special_symbols[key]:
                all_symbols_list.add(sym)

        all_symbols_list = list(all_symbols_list)
        self.symbol_storage = SymbolStorage(self.config, all_symbols_list)

    @abstractmethod
    def assign_special_sym_function(self):
        """ "Define custom symbol functions in game_override."""
        warn("No special symbol functions are defined")

    def reset_book(self) -> None:
        """Reset global simulation variables."""
        self.temp_wins = []
        self.board = [[[] for _ in range(self.config.num_rows[x])] for x in range(self.config.num_reels)]
        self.top_symbols = None
        self.bottom_symbols = None
        self.book_id = self.sim
        self.book = Book(self.book_id, self.criteria)
        self.win_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.win_manager.reset_end_round_wins()
        self.global_multiplier = 1
        self.final_win = 0
        self.tot_fs = 0
        self.fs = 0
        self.wincap_triggered = False
        self.triggered_freegame = False
        self.gametype = self.config.basegame_type
        self.repeat = False
        self.anticipation = [0] * self.config.num_reels

    def reset_seed(self, sim: int = 0, seed_override=None) -> None:
        """Reset rng seed to simulation number for reproducibility."""
        if seed_override is not None:
            random.seed(seed_override + 1)
        else:
            random.seed(sim + 1)
        self.sim = sim
        self.repeat_count = 0

    def reset_fs_spin(self) -> None:
        """Use if using repeat during freespin games."""
        self.triggered_freegame = True
        self.fs = 0
        self.gametype = self.config.freegame_type
        self.win_manager.reset_spin_win()

    def get_betmode(self, mode_name) -> object:
        """Return all current betmode information."""
        for betmode in self.config.bet_modes:
            if betmode.get_name() == mode_name:
                return betmode
        print("\nWarning: betmode couldn't be retrieved\n")

    def get_current_betmode(self) -> object:
        """Get current betmode information."""
        for betmode in self.config.bet_modes:
            if betmode.get_name() == self.betmode:
                return betmode

    def get_current_betmode_distributions(self) -> object:
        """Return current betmode criteria information."""
        dist = self.get_current_betmode().get_distributions()
        for c in dist:
            if c._criteria == self.criteria:
                return c
        raise RuntimeError("Could not locate criteria distribution.")

    def get_current_distribution_conditions(self) -> dict:
        """Return requirements for criteria setup/acceptance."""
        for d in self.get_betmode(self.betmode).get_distributions():
            if d._criteria == self.criteria:
                return d._conditions
        return RuntimeError("Could not locate betmode conditions")

    def check_current_repeat_count(self, warn_after_count: int = 1000):
        """Alert user to high repeat count."""
        if self.repeat_count >= warn_after_count and (self.repeat_count % warn_after_count) == 0:
            warn(
                f"\nHigh repeat count:\n Current Count: {self.repeat_count} \n Criteria: {self.criteria} \n Simulation: {self.sim}"
            )

    def record(self, description: dict) -> None:
        """
        Record functions must be used for distribution conditions.
        Freespin triggers are most commonly used, i.e {"kind": X, "symbol": "S", "gametype": "basegame"}
        It is recommended to otherwise record rare events with several keys in order to reduce the overall file-size containing many duplicate ids
        """
        dstr = {}
        for k, v in description.items():
            dstr[str(k)] = str(v)
        self.temp_wins.append(dstr)
        self.temp_wins.append(self.book_id)

    def check_force_keys(self, description) -> None:
        """Check and append unique force-key parameters."""
        current_mode_force_keys = self.get_current_betmode().get_force_keys()  # type:ignore
        for keyValue in description:
            if keyValue[0] not in current_mode_force_keys:
                self.get_current_betmode().add_force_key(keyValue[0])  # type:ignore

    def combine(self, modes, betmode_name) -> None:
        """Retrieve unique force record keys."""
        for modeConfig in modes:
            for betmode in modeConfig:
                if betmode.get_name() == betmode_name:
                    break
            force_keys = betmode.get_force_keys()  # type:ignore
            for key in force_keys:
                if key not in self.get_betmode(betmode_name).get_force_keys():  # type:ignore
                    self.get_betmode(betmode_name).add_force_key(key)  # type:ignore

    def imprint_wins(self) -> None:
        """Record all events to library if criteria conditions are satisfied."""
        for temp_win_index in range(int(len(self.temp_wins) / 2)):
            description = tuple(sorted(self.temp_wins[2 * temp_win_index].items()))
            book_id = self.temp_wins[2 * temp_win_index + 1]
            if description in self.recorded_events and (
                book_id not in self.recorded_events[description]["bookIds"]
            ):
                self.recorded_events[description]["timesTriggered"] += 1
                self.recorded_events[description]["bookIds"] += [book_id]
            elif description not in self.recorded_events:
                self.check_force_keys(description)
                self.recorded_events[description] = {
                    "timesTriggered": 1,
                    "bookIds": [book_id],
                }
        self.temp_wins = []
        self.library[self.sim + 1] = copy(self.book.to_json())
        self._payout_ints.append(self.library[self.sim + 1]["payoutMultiplier"])
        self.win_manager.update_end_round_wins()

    def update_final_win(self) -> None:
        """Separate base and freegame wins, verify the sum of there are equal to the final simulation payout."""
        final = round(min(self.win_manager.running_bet_win, self.config.wincap), 2)
        basewin = round(min(self.win_manager.basegame_wins, self.config.wincap), 2)
        freewin = round(min(self.win_manager.freegame_wins, self.config.wincap), 2)

        self.final_win = final
        self.book.payout_multiplier = self.final_win
        self.book.basegame_wins = basewin
        self.book.freegame_wins = freewin

        assert min(
            round(self.win_manager.basegame_wins + self.win_manager.freegame_wins, 2),
            self.config.wincap,
        ) == round(
            min(self.win_manager.running_bet_win, self.config.wincap), 2
        ), "Base + Free game payout mismatch!"
        assert min(
            round(self.book.basegame_wins + self.book.freegame_wins, 2),
            self.config.wincap,
        ) == min(
            round(self.book.payout_multiplier, 2), round(self.config.wincap, 2)
        ), "Base + Free game payout mismatch!"

    def check_repeat(self) -> None:
        """Checks if the spin failed a criteria constraint at any point."""
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

            if self.get_current_distribution_conditions()["force_freegame"] and not (self.triggered_freegame):
                self.repeat = True

        self.repeat_count += 1
        self.check_current_repeat_count()

    @abstractmethod
    def run_spin(self, sim, simulation_seed):
        """run_spin should be defined in gamestate."""
        print("Base Game is not implemented in this game. Currently passing when calling runSpin.")

    @abstractmethod
    def run_freespin(self):
        """run_freespin trigger function should be defined in gamestate."""
        print("gamestate requires def run_freespin(), currently passing when calling runFreeSpin")

    def run_sims(
        self,
        betmode_copy_list,
        betmode,
        sim_to_criteria,
        total_threads,
        total_repeats,
        num_sims,
        thread_index,
        repeat_count,
        compress=True,
        write_event_list=True,
        simulation_seeds=[],
    ) -> None:
        """Assigns criteria and runs individual simulations. Results are stored in temporary file to be combined when all threads are finished."""
        mode_max_win = None
        for bm in self.config.bet_modes:
            if bm._name.lower() == betmode.lower():
                mode_max_win = bm._wincap
        assert mode_max_win is not None

        self.win_manager = WinManager(self.config.basegame_type, self.config.freegame_type, mode_max_win)
        self.library = {}
        self.recorded_events = {}
        # 每个 bet mode 必须拥有独立的 payout sidecar；否则连续生成多个模式时，
        # 后一个模式会错误包含前一模式的 payout hash 和条目数。
        self._payout_ints = []
        self.betmode = betmode
        self.num_sims = num_sims
        stream_books = bool(getattr(self.config, "stream_books", False))
        temp_book_name = self.output_files.get_temp_multi_thread_name(
            betmode, thread_index, repeat_count, (compress) * True + (not compress) * False
        )
        if stream_books:
            if not compress or write_event_list:
                raise ValueError(
                    "stream_books 仅支持压缩 JSONL 且 write_event_list=False"
                )
            book_handle = open(temp_book_name, "wb")
            book_writer = zstd.ZstdCompressor().stream_writer(
                book_handle,
                closefd=False,
            )
            lookup_handle = open(
                self.output_files.get_temp_lookup_name(
                    betmode, thread_index, repeat_count
                ),
                "w",
                encoding="UTF-8",
            )
            segmented_handle = open(
                self.output_files.get_temp_segmented_name(
                    betmode, thread_index, repeat_count
                ),
                "w",
                encoding="UTF-8",
            )
            sidecar_handle = open(
                temp_book_name.rsplit(".", 2)[0] + ".payouts",
                "w",
                encoding="UTF-8",
            )

        try:
            for sim in range(
                thread_index * num_sims + (total_threads * num_sims) * repeat_count,
                (thread_index + 1) * num_sims + (total_threads * num_sims) * repeat_count,
            ):
                self.criteria = sim_to_criteria[sim]
                self.run_spin(sim, simulation_seeds[sim])
                if stream_books:
                    book = self.library.pop(sim + 1)
                    payout = book["payoutMultiplier"]
                    book_writer.write(
                        (json.dumps(book) + "\n").encode("UTF-8")
                    )
                    lookup_handle.write(f"{book['id']},1,{payout}\n")
                    segmented_handle.write(
                        f"{book['id']},{book['criteria']},"
                        f"{round(book['baseGameWins'], 2)},"
                        f"{round(book['freeGameWins'], 2)}\n"
                    )
                    sidecar_handle.write(f"{payout}\n")
                    self._payout_ints.clear()
        finally:
            if stream_books:
                book_writer.close()
                book_handle.close()
                lookup_handle.close()
                segmented_handle.close()
                sidecar_handle.close()
        mode_cost = self.get_current_betmode().get_cost()

        print(
            "Thread " + str(thread_index),
            "finished with",
            round(self.win_manager.total_cumulative_wins / (num_sims * mode_cost), 3),
            "RTP.",
            f"[baseGame: {round(self.win_manager.cumulative_base_wins/(num_sims*mode_cost), 3)}, freeGame: {round(self.win_manager.cumulative_free_wins/(num_sims*mode_cost), 3)}]",
            flush=True,
        )

        if not stream_books:
            write_json(self, temp_book_name, payout_ints=self._payout_ints)
        print_recorded_wins(self, self.output_files.get_temp_force_name(betmode, thread_index, repeat_count))
        if not stream_books:
            make_lookup_tables(self, self.output_files.get_temp_lookup_name(betmode, thread_index, repeat_count))
            make_lookup_pay_split(self, self.output_files.get_temp_segmented_name(betmode, thread_index, repeat_count))

        if write_event_list:
            write_library_events(self, list(self.library.values()), betmode)
        betmode_copy_list.append(self.config.bet_modes)
