#!/usr/bin/env python3
"""将已锁定的 base/bonus 百万局结果合并为 M2d 候选快照。"""

import json
from pathlib import Path


GAME_DIR = Path(__file__).resolve().parent
VALIDATION_DIR = GAME_DIR / "validation"
BASE_SOURCE = VALIDATION_DIR / "m2d_fast_base_fr0_8p129_1m.json"
BONUS_SOURCE = VALIDATION_DIR / "m2d_fast_bonus_frb0_8p243_1m.json"
OUTPUT = VALIDATION_DIR / "m2d_fast_1m_candidate.json"
CALIBRATION_FILES = {
    "initial": VALIDATION_DIR / "m2d_fast_1m_summary.json",
    "base_7p971": VALIDATION_DIR / "m2d_fast_base_fr0_7p971_1m.json",
    "base_8p100": VALIDATION_DIR / "m2d_fast_base_fr0_8p1_1m.json",
    "base_8p257": VALIDATION_DIR / "m2d_fast_base_fr0_8p257_1m.json",
    "base_8p129_selected": BASE_SOURCE,
    "base_8p171": VALIDATION_DIR / "m2d_fast_base_fr0_8p171_1m.json",
    "bonus_8p243_selected": BONUS_SOURCE,
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def current_reels() -> dict:
    return {
        reel: load(GAME_DIR / "reels" / f"{reel}.metadata.json")
        for reel in ("BR0", "FR0", "FRB0")
    }


def calibration_entry(label: str, path: Path) -> dict:
    data = load(path)
    return {
        "label": label,
        "source": path.name,
        "modes": {
            mode: {
                "rtp": result["rtp"],
                "rtp95ConfidenceInterval": result["rtp95ConfidenceInterval"],
                "simulationCount": result["simulationCount"],
            }
            for mode, result in data["modes"].items()
        },
    }


def main() -> None:
    base = load(BASE_SOURCE)
    bonus = load(BONUS_SOURCE)
    result = {
        "gameId": "0_0_sanguo_wuxing",
        "mathVersion": "m2d.0.0-candidate",
        "method": "eventless-exact-state-machine-v1",
        "seedContract": "string_to_int(criteria)+simulation_index",
        "status": "development-candidate-not-certified",
        "selectedReels": current_reels(),
        "modes": {
            "base": base["modes"]["base"],
            "bonus": bonus["modes"]["bonus"],
        },
        "sourceFiles": {
            "base": BASE_SOURCE.name,
            "bonus": BONUS_SOURCE.name,
        },
        "calibrationHistory": [
            calibration_entry(label, path)
            for label, path in CALIBRATION_FILES.items()
        ],
    }
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote={OUTPUT}")
    print(
        f"base={result['modes']['base']['rtp']:.8f} "
        f"bonus={result['modes']['bonus']['rtp']:.8f}"
    )


if __name__ == "__main__":
    main()
