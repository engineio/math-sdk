""" 
Obtain and compare file hash using SHA256
    Args:
    -f input arbitrary number of filepaths separated by whitespace
    Example:
    python3 get_file_hash.py -f '../games/0_0_ways/library/lookup_tables/lookUpTable_base.csv'

    -d specify a file directory and hash all files that do not end in .py
    [optional] -l the layer depth of the directory search, default to 1
    Example:
    python3 get_file_hash.py -d '../games/0_0_ways/library/lookup_tables/' -l 1
"""

import os
import hashlib
import argparse


def get_hash(filepath: str) -> str:
    """Get hexadecimal representation of data file."""
    sha_file = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha_file.update(data)
    hexrep = sha_file.hexdigest()
    return hexrep


def get_file_hash(*args: str) -> None:
    """Pass in a list of files to compare hash values"""
    hash_list = []
    for arg in args:
        file_hash = get_hash(arg)
        print(f"File: {arg.split("/")[-1]}\n{file_hash} \n\n")
        hash_list.append(file_hash)


def get_all_directory_hash(dir_path: str, folder_depth: int = 1) -> None:
    """Get all file-hash values from top-level directory"""
    files = []
    depth = 0
    for root, _, filepaths in os.walk(dir_path):
        files.extend(os.path.join(root, f) for f in filepaths)
        depth += 1
        if depth >= folder_depth:
            break

    for f in files:
        if not (f.endswith(".py")):
            get_file_hash(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", dest="files", nargs="+")
    parser.add_argument("-d", dest="dirs")
    parser.add_argument("-l", dest="depth", default=1, type=int)
    arguments = parser.parse_args()

    if arguments.files:
        get_file_hash(*arguments.files)
    elif arguments.dirs:
        get_all_directory_hash(arguments.dirs, arguments.depth)
