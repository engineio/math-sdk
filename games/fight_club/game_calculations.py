"""Fight Club — Cluster evaluation using KO Reels global multiplier."""

from src.executables.executables import Executables
from src.calculations.cluster import Cluster


class GameCalculations(Executables):
    """
    Uses the base Cluster.evaluate_clusters() with global_multiplier.
    No grid position multipliers — Fight Club uses a single KO Reels multiplier
    that grows with each cascade.
    """

    def get_clusters_update_wins(self):
        """Find clusters on board and update win manager using KO global multiplier."""
        clusters = Cluster.get_clusters(self.board, "wild")
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.board, self.win_data = Cluster.evaluate_clusters(
            config=self.config,
            board=self.board,
            clusters=clusters,
            global_multiplier=self.global_multiplier,
            return_data=return_data,
        )

        Cluster.record_cluster_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        self.win_manager.tumble_win = self.win_data["totalWin"]
