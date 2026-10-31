from game_calculations import GameCalculations
from src.calculations.cluster import Cluster
from src.calculations.statistics import get_random_outcome
from src.events.events import update_freespin_event, tumble_board_event
from game_events import update_grid_mult_event, rin_dash_event


class GameExecutables(GameCalculations):
    """Game dependent grouped functions."""

    def reset_grid_mults(self):
        """Initialize all grid position multipliers."""
        self.position_multipliers = [
            [0 for _ in range(self.config.num_rows[reel])] for reel in range(self.config.num_reels)
        ]

    def reset_rin_dash_stickies(self):
        """Rin Dash wilds persist only for the remaining tumbles of the current spin."""
        self.rin_dash_stickies = []

    def update_grid_mults(self):
        """All positions start with 1x. If there is a win in that position, the grid point
        is 'activated' and all subsequent wins on that position will double the grid value."""
        if self.win_data["totalWin"] > 0:
            for win in self.win_data["wins"]:
                for pos in win["positions"]:
                    if self.position_multipliers[pos["reel"]][pos["row"]] == 0:
                        self.position_multipliers[pos["reel"]][pos["row"]] = 1
                    else:
                        self.position_multipliers[pos["reel"]][pos["row"]] += 1
                        self.position_multipliers[pos["reel"]][pos["row"]] = min(
                            self.position_multipliers[pos["reel"]][pos["row"]], self.config.maximum_board_mult
                        )
            update_grid_mult_event(self)

    def get_clusters_update_wins(self):
        """Find clusters on board and update win manager."""
        clusters = Cluster.get_clusters(self.board, "wild")
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.board, self.win_data = self.evaluate_clusters_with_grid(
            config=self.config,
            board=self.board,
            clusters=clusters,
            pos_mult_grid=self.position_multipliers,
            global_multiplier=self.global_multiplier,
            return_data=return_data,
        )

        Cluster.record_cluster_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        self.win_manager.tumble_win = self.win_data["totalWin"]

    def update_freespin(self) -> None:
        """Called before a new reveal during freegame."""
        self.fs += 1
        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.tumblewin_mult = 0
        self.win_data = {}
        # Each Night Shift spin has its own dash stickies (not carried across freespins).
        self.reset_rin_dash_stickies()

    def tumble_game_board(self):
        """Remove winning symbols, cascade, then restore Rin Dash sticky wilds.

        tumble_board() (src/calculations/tumble.py) drops exploded cells and pulls
        new symbols from the reelstrip. Sticky wilds are position-locked for the
        rest of this spin, so they are written back after the cascade and before
        the next cluster evaluation. tumbleBoard is emitted from the raw cascade
        so the frontend can animate gravity; sticky cells are already known from
        the rinDash event(s) on this spin.
        """
        self.tumble_board()
        tumble_board_event(self)
        self.apply_rin_dash_stickies()

    def apply_rin_dash_stickies(self):
        """Force stored Rin Dash cells to wild W after a tumble."""
        if not getattr(self, "rin_dash_stickies", None):
            return
        for pos in self.rin_dash_stickies:
            reel, row = pos["reel"], pos["row"]
            self.board[reel][row] = self.create_symbol("W")
            self.board[reel][row].assign_attribute({"locked": True})
        self.get_special_symbols_on_board()

    def try_rin_dash(self, after_reveal: bool = False, force: bool = False) -> bool:
        """Roll for a Rin Dash. Night Shift reveal uses force=True (at least one per FS)."""
        if not force:
            weights = (
                self.config.rin_dash_reveal_chance if after_reveal else self.config.rin_dash_tumble_chance
            )
            if not get_random_outcome(weights):
                return False
        self.execute_rin_dash()
        return True

    def execute_rin_dash(self) -> None:
        """Pick a row or reel, convert those cells to sticky wilds, emit rinDash."""
        axis = get_random_outcome({"row": 1, "reel": 1})
        if axis == "row":
            line = get_random_outcome({i: 1 for i in range(self.config.num_rows[0])})
            positions = [{"reel": reel, "row": line} for reel in range(self.config.num_reels)]
        else:
            line = get_random_outcome({i: 1 for i in range(self.config.num_reels)})
            positions = [{"reel": line, "row": row} for row in range(self.config.num_rows[line])]

        for pos in positions:
            self.board[pos["reel"]][pos["row"]] = self.create_symbol("W")
            self.board[pos["reel"]][pos["row"]].assign_attribute({"locked": True})
            if pos not in self.rin_dash_stickies:
                self.rin_dash_stickies.append(pos)

        self.get_special_symbols_on_board()
        rin_dash_event(self, axis=axis, line=line, positions=positions)
