"""《三国五行传》M2c 自定义事件。"""

from copy import deepcopy


DUAL_WILD_TRIGGER_CANDIDATE = "dualWildTriggerCandidate"
MEGA_SYMBOLS_DETECTED = "megaSymbolsDetected"
RETURN_SYMBOL_MARKED = "returnSymbolMarked"
RETURN_WILDS_APPLIED = "returnWildsApplied"
RESCUE_APPLIED = "rescueApplied"
FEATURE_QUEUED = "featureQueued"
FEATURE_APPLIED = "featureApplied"
ROUND_MULTIPLIER_APPLIED = "roundMultiplierApplied"
RTP_COMPONENT_SUMMARY = "rtpComponentSummary"
SOUL_FREE_SPIN_TRIGGER = "soulFreeSpinTrigger"
DESTINY_WILD_COLLECTED = "destinyWildCollected"
SOUL_LEVEL_UP = "soulLevelUp"
SOUL_WILD_PLACED = "soulWildPlaced"
SOUL_WILD_CONSUMED = "soulWildConsumed"
SOUL_FREE_SPIN_SUMMARY = "soulFreeSpinSummary"


def _positions(items, include_padding=True):
    offset = 1 if include_padding else 0
    return [{"reel": reel, "row": row + offset} for reel, row in items]


def _board_snapshot(gamestate):
    return [
        [
            {
                "name": gamestate.board[reel][row].name,
                **(
                    {"wild": True}
                    if gamestate.board[reel][row].check_attribute("wild")
                    else {}
                ),
            }
            for row in range(gamestate.config.num_rows[reel])
        ]
        for reel in range(gamestate.config.num_reels)
    ]


def dual_wild_trigger_candidate_event(gamestate, w1_positions, w2_positions):
    event = {
        "index": len(gamestate.book.events),
        "type": DUAL_WILD_TRIGGER_CANDIDATE,
        "w1Positions": [{"reel": reel, "row": row + 1} for reel, row in w1_positions],
        "w2Positions": [{"reel": reel, "row": row + 1} for reel, row in w2_positions],
        "implementedFeature": True,
        "mathVersion": gamestate.config.math_version,
    }
    gamestate.book.add_event(event)


def soul_freespin_trigger_event(gamestate, source, w1_positions=None, w2_positions=None):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": SOUL_FREE_SPIN_TRIGGER,
            "source": source,
            "totalFs": gamestate.tot_fs,
            "w1Positions": _positions(w1_positions or []),
            "w2Positions": _positions(w2_positions or []),
            "mathVersion": gamestate.config.math_version,
        }
    )


def destiny_wild_collected_event(gamestate, positions):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": DESTINY_WILD_COLLECTED,
            "positions": _positions(positions),
            "count": len(positions),
            "level": gamestate.soul_level,
            "progress": gamestate.soul_level_progress,
            "nextThreshold": gamestate.soul_next_threshold(),
        }
    )


def soul_level_up_event(gamestate, added_spins):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": SOUL_LEVEL_UP,
            "level": gamestate.soul_level,
            "size": f"{gamestate.soul_level}x{gamestate.soul_level}",
            "multiplier": gamestate.soul_multiplier,
            "addedSpins": added_spins,
            "totalFs": gamestate.tot_fs,
        }
    )


def soul_wild_placed_event(gamestate):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": SOUL_WILD_PLACED,
            "level": gamestate.soul_level,
            "size": f"{gamestate.soul_level}x{gamestate.soul_level}",
            "multiplier": gamestate.soul_multiplier,
            "positions": _positions(gamestate.soul_positions),
        }
    )


def soul_wild_consumed_event(gamestate, winning_symbols):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": SOUL_WILD_CONSUMED,
            "level": gamestate.soul_level,
            "positions": _positions(gamestate.soul_positions),
            "winningSymbols": sorted(winning_symbols),
        }
    )


def soul_freespin_summary_event(gamestate):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": SOUL_FREE_SPIN_SUMMARY,
            "spinsPlayed": gamestate.fs,
            "totalSpinsAwarded": gamestate.tot_fs,
            "finalLevel": gamestate.soul_level,
            "collectedW2": gamestate.soul_total_collected,
            "freegameWin": int(round(gamestate.win_manager.freegame_wins * 100)),
        }
    )


def mega_symbols_detected_event(gamestate, groups):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": MEGA_SYMBOLS_DETECTED,
            "groups": [
                {
                    "symbol": group["symbol"],
                    "positions": _positions(sorted(group["positions"])),
                    "multiplier": gamestate.config.mega_multiplier,
                }
                for group in groups
            ],
        }
    )


def return_symbol_marked_event(gamestate, symbol):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": RETURN_SYMBOL_MARKED,
            "symbol": symbol,
        }
    )


def return_wilds_applied_event(gamestate, source_symbol, positions):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": RETURN_WILDS_APPLIED,
            "sourceSymbol": source_symbol,
            "positions": _positions(positions),
            "boardAfter": _board_snapshot(gamestate),
        }
    )


def rescue_applied_event(gamestate, positions):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": RESCUE_APPLIED,
            "positions": _positions(positions),
            "boardAfter": _board_snapshot(gamestate),
        }
    )


def feature_queued_event(gamestate, feature, charge):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": FEATURE_QUEUED,
            "feature": feature,
            "charge": charge,
            "queue": deepcopy(gamestate.feature_queue),
        }
    )


def feature_applied_event(gamestate, feature, phase, details):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": FEATURE_APPLIED,
            "feature": feature,
            "phase": phase,
            "details": deepcopy(details),
            "boardAfter": _board_snapshot(gamestate),
        }
    )


def round_multiplier_applied_event(gamestate, multiplier, raw_win, added_win):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": ROUND_MULTIPLIER_APPLIED,
            "executedFeatures": deepcopy(gamestate.executed_features),
            "multiplier": multiplier,
            "rawWin": int(round(raw_win * 100)),
            "addedWin": int(round(added_win * 100)),
            "totalWin": int(round(min(raw_win + added_win, gamestate.config.wincap) * 100)),
        }
    )


def rtp_component_summary_event(gamestate):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": RTP_COMPONENT_SUMMARY,
            "components": {
                name: int(round(value * 100))
                for name, value in sorted(gamestate.rtp_components.items())
                if value
            },
            "charge": gamestate.feature_charge,
            "executedFeatures": deepcopy(gamestate.executed_features),
        }
    )
