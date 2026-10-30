APPLY_TUMBLE_MULTIPLIER = "applyMultiplierToTumble"
UPDATE_GRID = "updateGrid"


def _clone(obj: object):
    t = type(obj)
    if t == dict:
        return {k: _clone(v) for k, v in obj.items()}
    elif t == list:
        return [_clone(x) for x in obj]
    return obj


def update_grid_mult_event(gamestate):
    """Pass updated position multipliers after a win."""
    event = {
        "index": len(gamestate.book.events),
        "type": UPDATE_GRID,
        "gridMultipliers": _clone(gamestate.position_multipliers),
    }
    gamestate.book.add_event(event)
