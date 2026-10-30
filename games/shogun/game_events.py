"""SHOGUN — Custom game events."""

from copy import deepcopy
from src.events.event_constants import EventConstants
from src.events.events import json_ready_sym

# Custom event type strings
EXPANDING_WILD      = "expandingWild"
UPDATE_STICKY_WILDS = "updateStickyWilds"
SCATTER_TRIGGER     = "scatterTrigger"


def expanding_wild_event(gamestate, reel_index: int, multiplier: int) -> None:
    """Emitted when a wild expands to fill an entire reel column."""
    offset = 1 if gamestate.config.include_padding else 0
    positions = [
        {"reel": reel_index, "row": row + offset}
        for row in range(gamestate.config.num_rows[reel_index])
    ]
    event = {
        "index":      len(gamestate.book.events),
        "type":       EXPANDING_WILD,
        "reel":       reel_index,
        "multiplier": multiplier,
        "positions":  positions,
    }
    gamestate.book.add_event(event)


def update_sticky_wilds_event(gamestate) -> None:
    """Emitted at the start of each free spin to show existing sticky wild reels."""
    existing = deepcopy(gamestate.sticky_wild_reels)
    event = {
        "index":           len(gamestate.book.events),
        "type":            UPDATE_STICKY_WILDS,
        "stickyWildReels": existing,
    }
    gamestate.book.add_event(event)


def scatter_trigger_event(gamestate, scatter_positions: list) -> None:
    """Emitted when 3 scatters trigger free spins."""
    offset = 1 if gamestate.config.include_padding else 0
    positions = deepcopy(scatter_positions)
    if gamestate.config.include_padding:
        for p in positions:
            p["row"] += 1

    event = {
        "index":            len(gamestate.book.events),
        "type":             SCATTER_TRIGGER,
        "totalFs":          gamestate.tot_fs,
        "scatterPositions": positions,
    }
    assert gamestate.tot_fs > 0, "tot_fs must be >0 when emitting scatterTrigger"
    gamestate.book.add_event(event)
