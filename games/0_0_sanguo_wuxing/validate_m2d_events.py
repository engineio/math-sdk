#!/usr/bin/env python3
"""验证 M2d 完整 Book 的前端事件顺序、字段和成长状态合同。"""

from __future__ import annotations

import argparse
import io
import json
from collections import Counter
from pathlib import Path

import zstandard


GAME_DIR = Path(__file__).resolve().parent
LEVEL_MULTIPLIERS = {1: 1, 2: 1, 3: 1, 4: 1, 5: 5, 6: 7, 7: 10}
LEVEL_ADDED_SPINS = {2: 4, 3: 3, 4: 2, 5: 2, 6: 1, 7: 1}


def assert_position(position: dict, event_type: str) -> tuple[int, int]:
    assert set(("reel", "row")).issubset(position), event_type
    reel, row = position["reel"], position["row"]
    assert 0 <= reel <= 6, (event_type, position)
    assert 1 <= row <= 7, (event_type, position)
    return reel, row


def assert_positions(event: dict, expected_count: int | None = None) -> list[tuple[int, int]]:
    positions = [
        assert_position(position, event["type"])
        for position in event.get("positions", [])
    ]
    assert len(positions) == len(set(positions)), event
    if expected_count is not None:
        assert len(positions) == expected_count, event
    return positions


def validate_book(book: dict, mode: str) -> Counter:
    assert set(("id", "payoutMultiplier", "events")).issubset(book)
    events = book["events"]
    assert events, book["id"]
    assert [event["index"] for event in events] == list(range(len(events))), book["id"]
    assert events[-1]["type"] == "finalWin", book["id"]
    assert events[-1]["amount"] == book["payoutMultiplier"], book["id"]

    counts = Counter(event["type"] for event in events)
    assert counts["finalWin"] == 1
    assert counts["soulFreeSpinSummary"] == counts["freeSpinEnd"]
    assert counts["soulWildConsumed"] <= counts["soulWildPlaced"]
    if mode == "bonus":
        assert counts["enterBonus"] == 1
        assert counts["soulFreeSpinTrigger"] == 1
        assert counts["soulFreeSpinSummary"] == 1
    else:
        assert counts["soulFreeSpinTrigger"] in (0, 1)
        assert counts["soulFreeSpinSummary"] == counts["soulFreeSpinTrigger"]

    for event in events:
        event_type = event["type"]
        if event_type == "soulFreeSpinTrigger":
            assert event["source"] in {"dualWild", "bonusBuy"}
            assert event["totalFs"] == 5
            for key in ("w1Positions", "w2Positions"):
                for position in event[key]:
                    assert_position(position, event_type)
        elif event_type == "destinyWildCollected":
            positions = assert_positions(event)
            assert event["count"] == len(positions) > 0
            assert 1 <= event["level"] <= 7
            assert event["progress"] >= 0
            assert event["nextThreshold"] in {None, 3, 4, 5}
        elif event_type == "soulLevelUp":
            level = event["level"]
            assert 2 <= level <= 7
            assert event["size"] == f"{level}x{level}"
            assert event["multiplier"] == LEVEL_MULTIPLIERS[level]
            assert event["addedSpins"] == LEVEL_ADDED_SPINS[level]
            assert event["totalFs"] >= 5
        elif event_type == "soulWildPlaced":
            level = event["level"]
            assert 1 <= level <= 7
            assert event["size"] == f"{level}x{level}"
            assert event["multiplier"] == LEVEL_MULTIPLIERS[level]
            assert_positions(event, expected_count=level * level)
        elif event_type == "soulWildConsumed":
            level = event["level"]
            assert 1 <= level <= 7
            assert_positions(event, expected_count=level * level)
            assert event["winningSymbols"]
        elif event_type == "soulFreeSpinSummary":
            assert 1 <= event["finalLevel"] <= 7
            assert event["spinsPlayed"] <= event["totalSpinsAwarded"]
            assert event["totalSpinsAwarded"] >= 5
            assert event["collectedW2"] >= 0
            assert event["freegameWin"] == int(round(book["freeGameWins"] * 100))
        elif event_type == "freeSpinEnd":
            assert event["amount"] == int(round(book["freeGameWins"] * 100))

    return counts


def validate_file(path: Path, mode: str, limit: int | None) -> dict:
    total_events = Counter()
    book_count = 0
    previous_id = None
    with path.open("rb") as handle:
        with zstandard.ZstdDecompressor().stream_reader(handle) as reader:
            for line in io.TextIOWrapper(reader, encoding="utf-8"):
                book = json.loads(line)
                if previous_id is not None:
                    assert book["id"] == previous_id + 1
                previous_id = book["id"]
                total_events.update(validate_book(book, mode))
                book_count += 1
                if limit is not None and book_count >= limit:
                    break
    assert book_count > 0
    return {
        "mode": mode,
        "bookCount": book_count,
        "firstBookId": previous_id - book_count + 1,
        "lastBookId": previous_id,
        "eventCounts": dict(sorted(total_events.items())),
        "status": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("base", "bonus"), required=True)
    parser.add_argument("--books", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    path = args.books or (
        GAME_DIR / "library" / "publish_files" / f"books_{args.mode}.jsonl.zst"
    )
    result = validate_file(path, args.mode, args.limit)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
