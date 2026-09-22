#!/bin/bash
set -e
cd /workspaces/math-sdk

echo "=== Patching events.py to remove double deepcopy ==="
cat > /tmp/patch_events.py << 'PYEOF'
import os

path = "env/src/stakeengine/src/events/events.py"
with open(path) as f:
    lines = f.readlines()

# Find and replace the win_info_event function body
output = []
i = 0
while i < len(lines):
    # Detect start of the old code block
    if "win_data_copy = {}" in lines[i]:
        # Skip all old lines until "gamestate.book.add_event(event)"
        while i < len(lines) and "gamestate.book.add_event(event)" not in lines[i]:
            i += 1
        i += 1  # skip the add_event line too

        # Insert new optimized code
        output.append("    wins = []\n")
        output.append("    for w in gamestate.win_data[\"wins\"]:\n")
        output.append("        if include_padding_index:\n")
        output.append("            new_positions = [{\"reel\": p[\"reel\"], \"row\": p[\"row\"] + 1} for p in w[\"positions\"]]\n")
        output.append("        else:\n")
        output.append("            new_positions = [{\"reel\": p[\"reel\"], \"row\": p[\"row\"]} for p in w[\"positions\"]]\n")
        output.append("        win_copy = {\n")
        output.append("            \"symbol\": w[\"symbol\"],\n")
        output.append("            \"kind\": w[\"kind\"],\n")
        output.append("            \"win\": int(round(min(w[\"win\"], gamestate.config.wincap) * 100, 0)),\n")
        output.append("            \"positions\": new_positions,\n")
        output.append("        }\n")
        output.append("        if \"meta\" in w:\n")
        output.append("            meta = dict(w[\"meta\"])\n")
        output.append("            meta[\"winWithoutMult\"] = int(min(w[\"meta\"][\"winWithoutMult\"] * 100, gamestate.config.wincap * 100))\n")
        output.append("            if \"overlay\" in meta and include_padding_index:\n")
        output.append("                meta[\"overlay\"] = dict(meta[\"overlay\"])\n")
        output.append("                meta[\"overlay\"][\"row\"] += 1\n")
        output.append("            win_copy[\"meta\"] = meta\n")
        output.append("        wins.append(win_copy)\n")
        output.append("\n")
        output.append("    event = {\n")
        output.append("        \"index\": len(gamestate.book.events),\n")
        output.append("        \"type\": EventConstants.WIN_DATA.value,\n")
        output.append("        \"totalWin\": int(round(min(gamestate.win_data[\"totalWin\"], gamestate.config.wincap) * 100, 0)),\n")
        output.append("        \"wins\": wins,\n")
        output.append("    }\n")
        output.append("    gamestate.book.add_event(event)\n")
    else:
        output.append(lines[i])
        i += 1

with open(path, "w") as f:
    f.writelines(output)
print("PATCHED events.py OK")
PYEOF

python3 /tmp/patch_events.py

echo "=== Pulling latest code ==="
git pull

echo "=== Running sims (1000 per mode, wincap=15000) ==="
cd games/shogun
python3 run.py
