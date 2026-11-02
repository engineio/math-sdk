"""Fight Club — Custom events for KO Reels and Death Match mechanics."""

KO_MULT_UPDATE = "koMultUpdate"
FIGHTER_TO_WILD = "fighterToWild"


def ko_mult_event(gamestate):
    """Emit the current KO Reels multiplier value after each cascade."""
    event = {
        "index": len(gamestate.book.events),
        "type": KO_MULT_UPDATE,
        "koMultiplier": gamestate.global_multiplier,
    }
    gamestate.book.add_event(event)


def fighter_wild_event(gamestate, fighter_symbol, positions):
    """Emit event when a random fighter is converted to WILD in Death Match."""
    event = {
        "index": len(gamestate.book.events),
        "type": FIGHTER_TO_WILD,
        "fighter": fighter_symbol,
        "positions": positions,
    }
    gamestate.book.add_event(event)
