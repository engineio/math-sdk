"""Events specific to new and updating expanding wild symbols."""

from src.events.event_constants import EventConstants
from src.events.events import json_ready_sym

NEW_EXP_WILDS = "newExpandingWilds"
UPDATE_EXP_WILDS = "updateExpandingWilds"
NEW_STICKY_SYMS = "newStickySymbols"
WIN_DATA = "winInfo"
PRIZE_WIN_DATA = "prizeWinInfo"


def _clone_wilds(obj: object):
    """Clone wild objects"""
    if isinstance(obj, list):
        return [_clone_wilds(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: _clone_wilds(v) for k, v in obj.items()}
    return obj


def new_expanding_wild_event(gamestate) -> None:
    """Passed after reveal event"""
    new_exp_wilds = gamestate.new_exp_wilds
    if gamestate.config.include_padding:
        for ew in new_exp_wilds:
            ew["row"] += 1

    event = {"index": len(gamestate.book.events), "type": NEW_EXP_WILDS, "newWilds": new_exp_wilds}
    gamestate.book.add_event(event)


def update_expanding_wild_event(gamestate) -> None:
    """On each reveal - the multiplier value on the expanding wild is updated (sent before reveal)"""
    existing_wild_details = _clone_wilds(gamestate.expanding_wilds)
    wild_event = []
    if gamestate.config.include_padding:
        for ew in existing_wild_details:
            if len(ew) > 0:
                ew["row"] += 1
                wild_event.append(ew)

    event = {"index": len(gamestate.book.events), "type": UPDATE_EXP_WILDS, "existingWilds": wild_event}
    gamestate.book.add_event(event)


def new_sticky_event(gamestate, new_sticky_syms: list):
    """Pass details on new prize symbols"""
    if gamestate.config.include_padding:
        for sym in new_sticky_syms:
            sym["row"] += 1
            sym["prize"] = int(sym["prize"] * 100)

    event = {"index": len(gamestate.book.events), "type": NEW_STICKY_SYMS, "newPrizes": new_sticky_syms}
    gamestate.book.add_event(event)


def win_info_prize_event(gamestate, include_padding_index=True):
    """
    include_padding_index: starts winning-symbol positions at row=1, to account for top/bottom symbol inclusion in board
    """
    win_data_copy = {}
    win_data_copy["wins"] = _clone_wilds(gamestate.win_data["wins"])
    prize_details = []
    for _, w in enumerate(win_data_copy["wins"]):
        if include_padding_index:
            prize_details.append({"reel": w["reel"], "row": w["row"] + 1, "prize": int(100 * w["value"])})
        else:
            prize_details.append({"reel": w["reel"], "row": w["row"], "prize": int(100 * w["value"])})

    event = {
        "index": len(gamestate.book.events),
        "type": PRIZE_WIN_DATA,
        "totalWin": int(round(min(gamestate.win_data["totalWin"], gamestate.config.wincap) * 100, 0)),
        "wins": prize_details,
    }
    gamestate.book.add_event(event)


def reveal_prize_event(gamestate):
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

    for idx, _ in enumerate(board_client):
        for idy, _ in enumerate(board_client[idx]):
            if board_client[idx][idy]["name"] != "X":
                board_client[idx][idy]["prize"] = int(board_client[idx][idy]["prize"] * 100)

    event = {
        "index": len(gamestate.book.events),
        "type": EventConstants.REVEAL.value,
        "board": board_client,
        "paddingPositions": gamestate.reel_positions,
        "gameType": "superspin",
        "anticipation": gamestate.anticipation,
    }
    gamestate.book.add_event(event)
