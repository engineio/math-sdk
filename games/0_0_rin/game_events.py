from copy import deepcopy

APPLY_TUMBLE_MULTIPLIER = "applyMultiplierToTumble"
UPDATE_GRID = "updateGrid"
RIN_DASH = "rinDash"


def update_grid_mult_event(gamestate):
    """Pass updated position multipliers after a win."""
    event = {
        "index": len(gamestate.book.events),
        "type": UPDATE_GRID,
        "gridMultipliers": deepcopy(gamestate.position_multipliers),
    }
    gamestate.book.add_event(event)


def rin_dash_event(gamestate, axis: str, line: int, positions: list):
    """Emit a Rin Dash: one full row or reel converted to sticky wilds for this spin."""
    event = {
        "index": len(gamestate.book.events),
        "type": RIN_DASH,
        "axis": axis,
        "line": line,
        "positions": deepcopy(positions),
    }
    gamestate.book.add_event(event)
