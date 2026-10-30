"Handles independent simulation events and details."


def _clone(obj: object):
    t = type(obj)
    if t is dict:
        return {k: _clone(v) for k, v in obj.items()}
    if t is list:
        return [_clone(x) for x in obj]
    return obj


class Book:
    "Stores simulation information."

    def __init__(self, book_id: int, criteria: str):
        "Initialize simulation book"
        self.id = book_id
        self.payout_multiplier = 0.0
        self.events = []
        self.criteria = criteria
        self.basegame_wins = 0.0
        self.freegame_wins = 0.0

    def add_event(self, event: dict, *, copy: bool = True):
        """Append event to book.
        copy=False skips the defensive copy; only pass it for events whose contents share no references with
        live game state (e.g. freshly built boards and win data)."""
        self.events.append(_clone(event) if copy else event)

    def append_book_items(self, event_id: int, appended_info: dict):
        "Modify an existing book event at position 'event_id'"
        for k, v in appended_info.items():
            self.events[event_id][k] = v

    def to_json(self):
        "Return JSON-ready object."
        json_book = {
            "id": self.id,
            "payoutMultiplier": int(round(self.payout_multiplier * 100, 0)),
            "events": self.events,
            "criteria": self.criteria,
            "baseGameWins": self.basegame_wins,
            "freeGameWins": self.freegame_wins,
        }
        return json_book
