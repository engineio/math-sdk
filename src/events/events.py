"""Defines reusable events"""

from src.events.event_constants import EventConstants
from src.state.books import _clone


def json_ready_sym(symbol: object, special_attributes: list = None):
    """Converts a symbol to dictionary/JSON format."""
    assert special_attributes is not None
    print_sym = {"name": symbol.name}

    for attr in special_attributes:
        value = getattr(symbol, attr, None)
        if value:
            print_sym[attr] = _clone(value)  # mutable attribute values must not be shared with the symbol
        elif attr in symbol.defn.special_flags:
            print_sym[attr] = True

    return print_sym


def reveal_event(gamestate):
    """Display the initial board drawn from reelstrips."""
    board_client = []
    special_attributes = list(gamestate.config.special_symbols.keys())
    for reel, _ in enumerate(gamestate.board):
        board_client.append([])
        for row in range(len(gamestate.board[reel])):
            board_client[reel].append(json_ready_sym(gamestate.board[reel][row], special_attributes))

    if gamestate.config.include_padding:
        for reel, _ in enumerate(board_client):
            board_client[reel] = [json_ready_sym(gamestate.top_symbols[reel], special_attributes)] + board_client[
                reel
            ]
            board_client[reel].append(json_ready_sym(gamestate.bottom_symbols[reel], special_attributes))

    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.REVEAL.value,
        "board": board_client,
        "paddingPositions": list(gamestate.reel_positions),
        "gameType": gamestate.gametype,
        "anticipation": list(gamestate.anticipation),
    }
    gamestate.book.add_event(event, copy=False)  # every value above is freshly built


def fs_trigger_event(
    gamestate,
    include_padding_index=True,
    basegame_trigger: bool = None,
    freegame_trigger: bool = None,
):
    """Triggers feature game from the basegame."""
    assert basegame_trigger != freegame_trigger, "must set either basegame_trigger or freeSpinTrigger to = True"
    event = {}
    scatter_positions = []
    for reel, _ in enumerate(gamestate.special_syms_on_board["scatter"]):
        scatter_positions.append(gamestate.special_syms_on_board["scatter"][reel])
    if include_padding_index:
        for pos in scatter_positions:
            pos["row"] += 1

    if basegame_trigger:
        event = {
            "index": len(gamestate.book.events),
            "type": EventConstants.FREESPINTRIGGER.value,
            "totalFs": gamestate.tot_fs,
            "positions": scatter_positions,
        }
    elif freegame_trigger:
        event = {
            "index": len(gamestate.book.events),
            "type": EventConstants.FREESPINRETRIGGER.value,
            "totalFs": gamestate.tot_fs,
            "positions": scatter_positions,
        }

    assert gamestate.tot_fs > 0, "total freegame (gamestate.tot_fs) must be >0"
    gamestate.book.add_event(event)


def set_win_event(gamestate, winlevel_key: str = "standard"):
    """Used for updating cumulative win ticker (for a single outcome)."""
    if not gamestate.wincap_triggered:
        event = {
            "index": len(gamestate.book.events),
            "type": EventConstants.SET_WIN.value,
            "amount": int(
                min(
                    round(gamestate.win_manager.spin_win * 100, 0),
                    gamestate.config.wincap * 100,
                )
            ),
            "winLevel": gamestate.config.get_win_level(gamestate.win_manager.spin_win, winlevel_key),
        }
        gamestate.book.add_event(event)


def set_total_event(gamestate):
    """Updates win amount for a betting round (including cumulative wins across multiple freespin wins)."""
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.SET_TOTAL_WIN.value,
        "amount": int(
            round(
                min(gamestate.win_manager.running_bet_win, gamestate.config.wincap) * 100,
                0,
            )
        ),
    }
    gamestate.book.add_event(event)


def set_tumble_event(gamestate):
    """Update banner indicating wins from successive tumbles."""
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.SET_TUMBLE_WIN.value,
        "amount": int(round(min(gamestate.tumble_win, gamestate.config.wincap) * 100)),
    }
    gamestate.book.add_event(event)


def wincap_event(gamestate):
    """Emit to indicate end of spin actions."""
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.WINCAP.value,
        "amount": int(
            round(
                min(gamestate.win_manager.running_bet_win, gamestate.config.wincap) * 100,
                0,
            )
        ),
    }
    gamestate.book.add_event(event)


def win_info_event(gamestate, include_padding_index=True):
    """
    include_padding_index: starts winning-symbol positions at row=1, to account for top/bottom symbol inclusion in board
    """
    win_data_copy = {}
    win_data_copy["wins"] = _clone(gamestate.win_data["wins"])
    for idx, w in enumerate(win_data_copy["wins"]):
        if include_padding_index:
            new_positions = []
            for p in w["positions"]:
                new_positions.append({"reel": p["reel"], "row": p["row"] + 1})
        else:
            new_positions = w["positions"]

        win_data_copy["wins"][idx]["win"] = int(
            round(min(win_data_copy["wins"][idx]["win"], gamestate.config.wincap) * 100, 0)
        )
        win_data_copy["wins"][idx]["positions"] = new_positions
        if "meta" in win_data_copy["wins"][idx]:
            win_data_copy["wins"][idx]["meta"]["winWithoutMult"] = int(
                int(
                    min(
                        win_data_copy["wins"][idx]["meta"]["winWithoutMult"] * 100,
                        gamestate.config.wincap * 100,
                    ),
                )
            )
            if "overlay" in win_data_copy["wins"][idx]["meta"] and include_padding_index:
                win_data_copy["wins"][idx]["meta"]["overlay"]["row"] += 1

    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.WIN_DATA.value,
        "totalWin": int(round(min(gamestate.win_data["totalWin"], gamestate.config.wincap) * 100, 0)),
        "wins": win_data_copy["wins"],
    }
    gamestate.book.add_event(event, copy=False)  # wins were cloned above


def update_tumble_win_event(gamestate):
    """Update a banner to record successive tumble wins."""
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.UPDATE_TUMBLE_WIN.value,
        "amount": int(round(min(gamestate.win_manager.spin_win, gamestate.config.wincap) * 100, 0)),
    }
    gamestate.book.add_event(event)


def update_freespin_event(gamestate):
    """Update the current spin number and total freegame"""
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.UPDATE_FS.value,
        "amount": int(gamestate.fs),
        "total": int(gamestate.tot_fs),
    }
    gamestate.book.add_event(event)


def freespin_end_event(gamestate, winlevel_key="endFeature"):
    """End of feature trigger."""
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.FREE_SPIN_END.value,
        "amount": int(round(min(gamestate.win_manager.freegame_wins, gamestate.config.wincap) * 100, 0)),
        "winLevel": gamestate.config.get_win_level(gamestate.win_manager.freegame_wins, winlevel_key),
    }
    gamestate.book.add_event(event)


def final_win_event(gamestate):
    """Assigns final payout multiplier for a simulation."""
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.FINAL_WIN.value,
        "amount": int(round(min(gamestate.final_win, gamestate.config.wincap) * 100, 0)),
    }
    gamestate.book.add_event(event)


def update_global_mult_event(gamestate):
    """Increment global multiplier value."""
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.UPDATE_GLOBAL_MULT.value,
        "globalMult": int(gamestate.global_multiplier),
    }

    gamestate.book.add_event(event)


def tumble_board_event(gamestate):
    """States the symbol positions removed from a board during tumble, and which new symbols should take their place."""
    special_attributes = list(gamestate.config.special_symbols.keys())

    exploding = []
    for win in gamestate.win_data["wins"]:
        for pos in win["positions"]:
            if gamestate.config.include_padding:
                exploding.append({"reel": pos["reel"], "row": pos["row"] + 1})
            else:
                exploding.append({"reel": pos["reel"], "row": pos["row"]})

    exploding = sorted(exploding, key=lambda x: x["reel"])

    new_symbols = [[] for _ in range(gamestate.config.num_reels)]
    for r, _ in enumerate(gamestate.new_symbols_from_tumble):
        if len(gamestate.new_symbols_from_tumble[r]) > 0:
            new_symbols[r] = [json_ready_sym(s, special_attributes) for s in gamestate.new_symbols_from_tumble[r]]

    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.TUMBLE_BOARD.value,
        "newSymbols": new_symbols,
        "explodingSymbols": exploding,
    }
    gamestate.book.add_event(event, copy=False)  # every value above is freshly built


def enter_bonus_event(gamestate) -> None:
    "Indicate feature game entry explicitly."
    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.ENTER_BONUS.value,
        "reason": gamestate.bonus_type,
    }
    gamestate.book.add_event(event)
