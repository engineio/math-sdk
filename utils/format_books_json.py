#!/usr/bin/env python3
"""
Script to format books files after simulation runs
This script will format simple name objects to single lines while keeping complex objects pretty-printed
Supports both JSON and JSONL formats
Only processes files with "books" in their name within the games directory
"""

import json
import re
import sys
from pathlib import Path


def is_valid_jsonl(content):
    """Check if content is valid JSONL format"""
    lines = content.strip().split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
        except json.JSONDecodeError:
            return False
    return True


def reconstruct_jsonl(content):
    """Attempt to reconstruct valid JSONL from corrupted content"""
    # Try to find complete JSON objects by looking for balanced braces
    json_objects = []
    current_object = ""
    brace_count = 0
    in_string = False
    escape_next = False

    for char in content:
        if escape_next:
            escape_next = False
            current_object += char
            continue

        if char == "\\":
            escape_next = True
            current_object += char
            continue

        if char == '"' and not escape_next:
            in_string = not in_string

        if not in_string:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1

        current_object += char

        # If we have a complete object (brace_count == 0 and we've seen at least one {)
        if brace_count == 0 and current_object.strip() and "{" in current_object:
            try:
                # Try to parse as JSON
                parsed = json.loads(current_object.strip())
                json_objects.append(json.dumps(parsed, separators=(",", ":")))
                current_object = ""
            except json.JSONDecodeError:
                # If parsing fails, continue building the object
                pass

    return "\n".join(json_objects)


def format_json_with_compact_names(data):
    """Format JSON with compact simple name objects"""
    # Convert to pretty-printed JSON
    pretty_json = json.dumps(data, indent=2)

    # Use regex to find and compact simple name objects
    # Pattern: "name": "value" (with potential whitespace)
    # (\s also matches newlines, so this covers simple objects spread over several lines too)
    compact_pattern = r'{\s*"name":\s*"([^"]+)"\s*}'
    pretty_json = re.sub(compact_pattern, r'{"name": "\1"}', pretty_json)

    return pretty_json


def format_jsonl_lines(lines, skip_invalid):
    """Format each JSONL line. Invalid lines are skipped with a warning, or (skip_invalid=False) return None."""
    formatted_lines = []
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue  # Skip empty lines in JSONL

        try:
            # Parse JSON
            data = json.loads(line)
        except json.JSONDecodeError as e:
            if not skip_invalid:
                return None
            print(f"  ⚠️  Warning: Invalid JSON on line {line_num}: {e}")
            print(f"       Line content: {line[:100]}...")
            # Skip invalid lines instead of keeping them
            continue
        # Format with compact names
        formatted_lines.append(format_json_with_compact_names(data))
    return formatted_lines


def process_json_file(file_path):
    """Process a single JSON or JSONL file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Determine if this is a JSON or JSONL file
        is_jsonl = file_path.suffix == ".jsonl"

        if is_jsonl:
            # Handle JSONL format
            # Each line is parsed once. If any line is invalid (file corrupted), reconstruct JSONL and format that.
            lines = content.strip().split("\n")
            formatted_lines = format_jsonl_lines(lines, skip_invalid=False)
            if formatted_lines is None:
                print(f"  ⚠️  File appears corrupted, attempting to reconstruct JSONL format...")
                content = reconstruct_jsonl(content)
                lines = content.strip().split("\n")
                formatted_lines = format_jsonl_lines(lines, skip_invalid=True)

            # Write back to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(formatted_lines))
                if formatted_lines and formatted_lines[-1]:  # Add final newline if content exists
                    f.write("\n")

            return len(lines)

        else:
            # Handle JSON format
            try:
                # For large single-line JSON arrays, we need a more memory-efficient approach
                # First, try to parse normally
                try:
                    data = json.loads(content)
                    # Format with compact names
                    formatted = format_json_with_compact_names(data)

                    # Write back to file
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(formatted)
                        f.write("\n")

                    return 1  # Single JSON object processed

                except json.JSONDecodeError as e:
                    # If normal parsing fails, try to handle as large array on single line
                    print(f"  ⚠️  Standard JSON parsing failed, attempting array parsing: {e}")
                    return process_large_json_array(file_path, content)

            except Exception as e:
                print(f"  ❌ Error processing JSON file: {e}")
                return 0

    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return 0


def process_large_json_array(file_path, content):
    """Process a large JSON array stored on a single line by extracting individual objects"""
    try:
        # Strip whitespace and check if it's an array
        content = content.strip()
        if not (content.startswith("[") and content.endswith("]")):
            print(f"  ⚠️  Content doesn't appear to be a JSON array")
            return 0

        # Remove the outer brackets
        array_content = content[1:-1].strip()

        # Split the array content into individual JSON objects
        # We need to be careful about commas inside strings and nested objects
        json_objects = []
        current_object = ""
        brace_count = 0
        bracket_count = 0
        in_string = False
        escape_next = False

        i = 0
        while i < len(array_content):
            char = array_content[i]

            if escape_next:
                escape_next = False
                current_object += char
                i += 1
                continue

            if char == "\\":
                escape_next = True
                current_object += char
                i += 1
                continue

            if char == '"':
                in_string = not in_string

            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                elif char == "[":
                    bracket_count += 1
                elif char == "]":
                    bracket_count -= 1
                elif char == "," and brace_count == 0 and bracket_count == 0:
                    # This comma separates top-level objects
                    if current_object.strip():
                        obj_content = current_object.strip()
                        try:
                            # Parse and validate the JSON object
                            parsed = json.loads(obj_content)
                            json_objects.append(parsed)
                        except json.JSONDecodeError as e:
                            # Try to fix common issues with trailing characters
                            # Sometimes there might be extra characters after the JSON object
                            try:
                                # Find the last complete JSON object by counting braces
                                temp_brace_count = 0
                                last_valid_pos = -1
                                temp_in_string = False
                                temp_escape = False

                                for j, c in enumerate(obj_content):
                                    if temp_escape:
                                        temp_escape = False
                                        continue
                                    if c == "\\":
                                        temp_escape = True
                                        continue
                                    if c == '"':
                                        temp_in_string = not temp_in_string
                                    if not temp_in_string:
                                        if c == "{":
                                            temp_brace_count += 1
                                        elif c == "}":
                                            temp_brace_count -= 1
                                            if temp_brace_count == 0:
                                                last_valid_pos = j + 1
                                                break

                                if last_valid_pos > 0:
                                    clean_obj = obj_content[:last_valid_pos]
                                    parsed = json.loads(clean_obj)
                                    json_objects.append(parsed)
                                    print(f"  ✅ Recovered malformed JSON object by truncating extra data")
                                else:
                                    print(f"  ⚠️  Warning: Could not recover malformed JSON object: {e}")
                                    print(f"       Object content: {obj_content[:100]}...")
                            except json.JSONDecodeError:
                                print(f"  ⚠️  Warning: Invalid JSON object: {e}")
                                print(f"       Object content: {obj_content[:100]}...")
                    current_object = ""
                    i += 1
                    continue

            current_object += char
            i += 1

        # Don't forget the last object
        if current_object.strip():
            obj_content = current_object.strip()
            try:
                parsed = json.loads(obj_content)
                json_objects.append(parsed)
            except json.JSONDecodeError as e:
                # Try to fix common issues with trailing characters
                try:
                    # Find the last complete JSON object by counting braces
                    temp_brace_count = 0
                    last_valid_pos = -1
                    temp_in_string = False
                    temp_escape = False

                    for j, c in enumerate(obj_content):
                        if temp_escape:
                            temp_escape = False
                            continue
                        if c == "\\":
                            temp_escape = True
                            continue
                        if c == '"':
                            temp_in_string = not temp_in_string
                        if not temp_in_string:
                            if c == "{":
                                temp_brace_count += 1
                            elif c == "}":
                                temp_brace_count -= 1
                                if temp_brace_count == 0:
                                    last_valid_pos = j + 1
                                    break

                    if last_valid_pos > 0:
                        clean_obj = obj_content[:last_valid_pos]
                        parsed = json.loads(clean_obj)
                        json_objects.append(parsed)
                        print(f"  ✅ Recovered malformed JSON object by truncating extra data")
                    else:
                        print(f"  ⚠️  Warning: Could not recover malformed JSON object: {e}")
                        print(f"       Object content: {obj_content[:100]}...")
                except json.JSONDecodeError:
                    print(f"  ⚠️  Warning: Invalid JSON object: {e}")
                    print(f"       Object content: {obj_content[:100]}...")

        if not json_objects:
            print(f"  ⚠️  No valid JSON objects found in array")
            return 0

        print(f"  ✅ Successfully parsed {len(json_objects)} JSON objects from array")

        # Format the entire array with compact names
        formatted = format_json_with_compact_names(json_objects)

        # Write back to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted)
            f.write("\n")

        return len(json_objects)

    except Exception as e:
        print(f"  ❌ Error processing large JSON array: {e}")
        return 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 format_books_json.py <game_directory>")
        print("Example: python3 format_books_json.py games/0_0_tower_defense")
        sys.exit(1)

    game_dir = Path(sys.argv[1])

    if not game_dir.exists():
        print(f"Error: Game directory '{game_dir}' does not exist")
        sys.exit(1)

    # Find all .json and .jsonl files with "books" in their name in the game directory
    json_files = [f for f in game_dir.glob("**/*.json") if "books" in f.name.lower()]
    jsonl_files = [f for f in game_dir.glob("**/*.jsonl") if "books" in f.name.lower()]
    all_files = json_files + jsonl_files

    if not all_files:
        print(f"No .json or .jsonl files with 'books' in their name found in {game_dir}")
        sys.exit(0)

    print("Formatting books files (JSON and JSONL)...")

    total_lines = 0
    for file_path in all_files:
        print(f"  Formatting: {file_path}")
        lines_processed = process_json_file(file_path)
        if lines_processed > 0:
            print(f"  ✅ Formatted: {file_path} ({lines_processed} lines processed)")
            total_lines += lines_processed

    print(f"Books formatting complete! ({total_lines} total lines processed)")


if __name__ == "__main__":
    main()
