"""不写模拟库的快速回合烟雾测试。"""

import json

from game_config import GameConfig
from gamestate import GameState


def main():
    config = GameConfig()
    state = GameState(config)
    state.betmode = "base"
    state.criteria = "basegame"
    state.run_spin(sim=360, simulation_seed=0x36072026)
    book = state.library[361]

    assert book["payoutMultiplier"] <= config.wincap * 100
    assert book["events"]
    assert book["events"][-1]["type"] == "finalWin"
    print(
        json.dumps(
            {
                "gameID": config.game_id,
                "mathVersion": config.math_version,
                "payoutMultiplierX": book["payoutMultiplier"] / 100,
                "eventCount": len(book["events"]),
                "eventTypes": [event["type"] for event in book["events"]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
