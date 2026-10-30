"""Handles writing all game game files"""

from collections import defaultdict
from warnings import warn
import shutil
import os
import hashlib
import json
import pickle as _pickle
import zstandard as zstd


def get_sha_256(file_to_hash: str):
    """Get human readable hash of file."""
    try:
        with open(file_to_hash, "rb") as f:
            sha256_file = hashlib.sha256()
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256_file.update(data)
        sha256_hexRep = sha256_file.hexdigest()
    except FileNotFoundError:
        warn(f"{file_to_hash} is empty.\nCould not create hash")
        sha256_hexRep = ""
    return sha256_hexRep


def make_force_json(gamestate: object):
    """Construct force-file from recorded description keys."""
    folder_path = gamestate.config.force_path
    force_file_path = os.path.join(folder_path, "force.json")

    if os.path.isfile(force_file_path) and os.path.getsize(force_file_path) > 0:
        try:
            with open(force_file_path, "r", encoding="UTF-8") as force_file:
                force_data = json.load(force_file)
        except json.JSONDecodeError:
            print("Error decoding JSON: The file may be corrupted or empty.")
            force_data = {}
    else:
        force_data = {}

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.endswith(".json") and filename.startswith("force_record_"):
            with open(file_path, mode="r", encoding="UTF-8") as file:
                data = json.load(file)

                modename = filename[len("force_record_") : -len(".json")]
                force_data[modename] = {}

                if isinstance(data, list):
                    for item in data:
                        for key, value in item["search"].items():
                            if key not in force_data[modename]:
                                force_data[modename][key] = []
                            if value not in force_data[modename][key]:
                                force_data[modename][key] += [value]
                else:
                    print("Expected a list, found:", type(data))

    with open(force_file_path, "w", encoding="UTF-8") as force_file:
        json.dump(force_data, force_file, indent=4)


def get_force_options(force_results: dict):
    """Return JSON ready force keys."""
    force_keys = defaultdict(set)
    for force in force_results.keys():
        for key, val in force:
            force_keys[str(key)].add(val)
    return {key: list(val) for key, val in force_keys.items()}


def make_lookup_tables(gamestate: object, name: str):
    """Write lookup tables for all simulations."""
    file = open(name, "w", encoding="UTF-8")
    sims = list(gamestate.library.keys())
    sims.sort()
    for sim in sims:
        file.write("{},1,{}\n".format(gamestate.library[sim]["id"], gamestate.library[sim]["payoutMultiplier"]))
    file.close()


def make_lookup_pay_split(gamestate: object, name: str):
    """Record win values from basegame and freegame types."""
    file = open(name, "w", encoding="UTF-8")
    sims = list(gamestate.library.keys())
    sims.sort()
    for sim in sims:
        file.write(
            str(gamestate.library[sim]["id"])
            + ","
            + str(gamestate.library[sim]["criteria"])
            + ","
            + str(round(gamestate.library[sim]["baseGameWins"], 2))
            + ","
            + str(round(gamestate.library[sim]["freeGameWins"], 2))
            + "\n"
        )
    file.close()


def write_library_events(gamestate: object, library: list, gametype: str):
    """Write all unique events within a given mode - with one example application."""
    unique_event = []
    event_items = {}
    for event in library:
        for instance in event["events"]:
            lib_event = instance["type"]
            if lib_event not in unique_event:
                unique_event.append(lib_event)
                item_keys = instance.keys()
                dict_details = {key: instance[key] for key in item_keys if key != "index"}
                event_items[lib_event] = dict_details
    json_object = json.dumps(event_items, indent=4)
    with open(
        os.path.join(gamestate.output_files.config_path, f"event_config_{gametype}.json"),
        "w",
        encoding="UTF-8",
    ) as f:
        f.write(json_object)


def output_lookup_and_force_files(
    threads: int,
    batching_size: int,
    game_id: str,
    betmode: str,
    gamestate: object,
    num_sims: int = 1000000,
    compress: bool = True,
):
    """Combine temporary lookup tables and force files into a single output."""
    print("Saving books for ", game_id, "in", betmode)
    num_repeats = max(int(round(num_sims / threads / batching_size, 0)), 1)
    file_list = []
    for repeat_index in range(num_repeats):
        for thread in range(threads):
            file_list.append(
                gamestate.output_files.get_temp_multi_thread_name(betmode, thread, repeat_index, compress)
            )

    if compress:
        final_out = gamestate.output_files.get_final_book_name(betmode, True)
        # All simulation workers have finished, so use every core. Output is identical for any thread count >= 1.
        compressor = zstd.ZstdCompressor(threads=-1)
        with open(final_out, "wb") as f_out:
            with compressor.stream_writer(f_out, closefd=False) as writer:
                for fname in file_list:
                    dctx = zstd.ZstdDecompressor()
                    with open(fname, "rb") as f_in:
                        with dctx.stream_reader(f_in) as reader:
                            while True:
                                chunk = reader.read(65536)
                                if not chunk:
                                    break
                                writer.write(chunk)
    else:
        with open(
            gamestate.output_files.get_final_book_name(betmode, False),
            "w",
            encoding="UTF-8",
        ) as outfile:
            for id, filename in enumerate(file_list):
                with open(filename, "r", encoding="UTF-8") as infile:
                    file_data = infile.read()
                    if filename.endswith(".jsonl"):
                        outfile.write(file_data)
                    elif filename.endswith(".json"):
                        if id == 0 and len(file_list) == 1:
                            outfile.write(file_data)
                        elif id == 0 and len(file_list) > 1:
                            outfile.write(file_data[:-1])  # don't write final ']'
                        elif id != len(file_list) - 1:
                            outfile.write("," + file_data[1:-1])  # don't write first or last '[/]'
                        else:
                            outfile.write("," + file_data[1::])  # dont write first '[', write last ']'

    print("Saving force files for", game_id, "in", betmode)
    force_results_dict = {}
    file_list = []
    for repeat_index in range(num_repeats):
        for thread in range(threads):
            file_list.append(
                gamestate.output_files.get_temp_force_name(betmode, thread, repeat_index),
            )

    for filename in file_list:
        with open(filename, "rb") as f:
            force_chunk = _pickle.load(f)
        for key in force_chunk:
            if force_results_dict.get(key) is not None:
                force_results_dict[key]["timesTriggered"] += force_chunk[key]["timesTriggered"]
                force_results_dict[key]["bookIds"] += force_chunk[key]["bookIds"]
            else:
                force_results_dict[key] = force_chunk[key]

    force_results_dict_just_for_rob = []
    for force_combination in force_results_dict:
        search_dict = []
        for key in force_combination:
            search_dict.append({"name": str(key[0]), "value": str(key[1])})
        force_dict = {
            "search": search_dict,
            "timesTriggered": force_results_dict[force_combination]["timesTriggered"],
            "bookIds": force_results_dict[force_combination]["bookIds"],
        }
        force_results_dict_just_for_rob.append(force_dict)

    json_object_for_rob = json.dumps(force_results_dict_just_for_rob, indent=4)
    force_record_path = os.path.join(gamestate.output_files.force_path, f"force_record_{betmode}.json")
    with open(force_record_path, "w", encoding="UTF-8") as file:
        file.write(json_object_for_rob)

    forceResultKeys = get_force_options(force_results_dict)
    json_file_path = os.path.join(gamestate.output_files.force_path, "force.json")
    try:
        with open(json_file_path, "r", encoding="UTF-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    data[gamestate.get_current_betmode().get_name()] = forceResultKeys
    json_object = json.dumps(data, indent=4)
    with open(json_file_path, "w", encoding="UTF-8") as file:
        file.write(json_object)

    weights_plus_wins_file_list = []
    segmented_lut_file_list = []
    print("Saving LUTs for", game_id, "in", betmode)
    for repeat_index in range(num_repeats):
        for thread in range(threads):
            weights_plus_wins_file_list += [
                gamestate.output_files.get_temp_lookup_name(betmode, thread, repeat_index)
            ]
            segmented_lut_file_list += [
                gamestate.output_files.get_temp_segmented_name(betmode, thread, repeat_index)
            ]

    with open(
        gamestate.output_files.get_final_lookup_name(betmode),
        "w",
        encoding="UTF-8",
    ) as outfile:
        for filename in weights_plus_wins_file_list:
            with open(filename, "r", encoding="UTF-8") as infile:
                outfile.write(infile.read())

    # Write _0 file if it does not exist
    if not (os.path.exists(gamestate.output_files.get_optimized_lookup_name(betmode))):
        shutil.copy(
            gamestate.output_files.get_final_lookup_name(betmode),
            gamestate.output_files.get_optimized_lookup_name(betmode),
        )
    with open(
        gamestate.output_files.get_final_segmented_name(betmode),
        "w",
        encoding="UTF-8",
    ) as outfile:
        for filename in segmented_lut_file_list:
            with open(filename, "r", encoding="UTF-8") as infile:
                outfile.write(infile.read())

    # Build verification.json from payout sidecars
    sidecar_list = []
    for repeat_index in range(num_repeats):
        for thread in range(threads):
            temp_name = gamestate.output_files.get_temp_multi_thread_name(betmode, thread, repeat_index, compress)
            sidecar_name = temp_name.rsplit(".", 2)[0] + ".payouts"
            if os.path.exists(sidecar_name):
                sidecar_list.append(sidecar_name)
    if sidecar_list:
        merged_payouts = []
        for sc in sidecar_list:
            with open(sc, "r", encoding="UTF-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        merged_payouts.append(int(line))

        payout_hash = hashlib.md5(_pickle.dumps(merged_payouts)).hexdigest()
        book_file = gamestate.output_files.get_final_book_name(betmode, compress)
        file_hash = get_sha_256(book_file)

        verification = {
            "payout_hash": payout_hash,
            "file_hash": file_hash,
            "num_entries": len(merged_payouts),
        }
        verification_path = os.path.join(gamestate.output_files.config_path, f"books_{betmode}.verification.json")
        with open(verification_path, "w", encoding="UTF-8") as f:
            json.dump(verification, f, indent=2)
        print(f"Wrote verification file: {verification_path}")


def write_json(gamestate, filename: str, payout_ints=None):
    """Convert the list of dictionaries to a JSON-encoded string and compress it in chunks."""
    json_objects = gamestate._library_lines  # books are JSON-encoded once, at imprint_wins()
    combined_data = "\n".join(json_objects) + "\n"

    if filename.endswith(".zst"):
        compressor = zstd.ZstdCompressor()
        compressed_data = compressor.compress(combined_data.encode("UTF-8"))
        with open(filename, "wb") as f:
            f.write(compressed_data)
    else:
        with open(filename, "w", encoding="UTF-8") as f:
            if not (gamestate.config.output_regular_json):
                f.write(combined_data)
            else:
                # identical to json.dumps(list_of_books)
                f.write("[" + ", ".join(json_objects) + "]")

    # Write payout sidecar if captured at imprint_wins
    if payout_ints is not None:
        sidecar_name = filename.rsplit(".", 2)[0] + ".payouts"
        with open(sidecar_name, "w", encoding="UTF-8") as f:
            for p in payout_ints:
                f.write(f"{p}\n")


def print_recorded_wins(gamestate: object, name: str = ""):
    """Temporary file generation for wins/recorded results."""
    with open(name, "wb") as file:
        _pickle.dump(gamestate.recorded_events, file, protocol=_pickle.HIGHEST_PROTOCOL)
