"""Export deterministic, high-signal M2d Books for the M2e frontend demo.

The source Book files remain the RGS-compatible zstd JSONL artifacts. This
script only selects representative records and writes browser-friendly JSON.
"""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from typing import Any

import zstandard as zstd


PUBLISH_DIR = Path(__file__).parent / "library" / "publish_files"


def final_level(book: dict[str, Any]) -> int:
    summaries = [
        event.get("finalLevel", 0)
        for event in book.get("events", [])
        if event.get("type") == "soulFreeSpinSummary"
    ]
    return max(summaries, default=0)


def select_book(path: Path) -> dict[str, Any]:
    selected: dict[str, Any] | None = None
    selected_key: tuple[int, int, int] | None = None

    with path.open("rb") as source:
        with zstd.ZstdDecompressor().stream_reader(source) as reader:
            text = io.TextIOWrapper(reader, encoding="utf-8")
            for line in text:
                book = json.loads(line)
                key = (
                    final_level(book),
                    int(book.get("payoutMultiplier", 0)),
                    -int(book.get("id", 0)),
                )
                if selected_key is None or key > selected_key:
                    selected = book
                    selected_key = key

    if selected is None:
        raise RuntimeError(f"No Books found in {path}")
    return selected


def first_books(path: Path, limit: int) -> list[dict[str, Any]]:
    books: list[dict[str, Any]] = []
    with path.open("rb") as source:
        with zstd.ZstdDecompressor().stream_reader(source) as reader:
            text = io.TextIOWrapper(reader, encoding="utf-8")
            for line in text:
                books.append(json.loads(line))
                if len(books) >= limit:
                    break
    if len(books) < limit:
        raise RuntimeError(f"Expected {limit} Books in {path}, found {len(books)}")
    return books


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "mathVersion": "m2d.0.0-candidate",
        "grid": "7x7",
        "visibleRows": [1, 7],
        "books": {},
    }
    for mode in ("base", "bonus"):
        source_path = PUBLISH_DIR / f"books_{mode}.jsonl.zst"
        book = select_book(source_path)
        output = args.output_dir / f"{mode}.json"
        output.write_text(
            json.dumps(book, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest["books"][mode] = {
            "file": f"{mode}.json",
            "id": book["id"],
            "payoutMultiplier": book["payoutMultiplier"],
            "finalLevel": final_level(book),
            "eventCount": len(book["events"]),
        }
        pool_size = 200 if mode == "base" else 100
        pool = first_books(source_path, pool_size)
        pool_output = args.output_dir / f"{mode}-pool.json"
        pool_output.write_text(
            json.dumps(
                {
                    "mode": mode,
                    "mathVersion": "m2d.0.0-candidate",
                    "selection": "sequential-certified-book-pool",
                    "books": pool,
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        manifest["books"][f"{mode}Pool"] = {
            "file": pool_output.name,
            "count": len(pool),
            "firstBookId": pool[0]["id"],
            "lastBookId": pool[-1]["id"],
        }

    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
