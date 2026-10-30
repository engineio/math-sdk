"""Test file decompression and validate data structure is valid JSON."""

import json
import io
import zstandard as zstd


def decompress(input_path: str, save_output: bool = False):
    """Decompress zst files assuming newline char to indicate different sims."""

    def json_validate(json_blob):
        """Validate each uncompressed result to ensure valid json format."""
        try:
            _ = json.loads(json_blob)
        except json.decoder.JSONDecodeError:
            print("Invalid JSON!")
            raise RuntimeError("Invalid JSON")

    decompressor = zstd.ZstdDecompressor()
    with open(input_path, "rb") as f:
        with decompressor.stream_reader(f) as reader:
            txt_stream = io.TextIOWrapper(reader, encoding="utf-8")
            lines = []
            for line in txt_stream:
                if line.strip():
                    json_validate(line)
                    if save_output:
                        lines.append(line)

    if save_output:
        with open("decompressed.jsonl", "w", encoding="UTF-8") as f:
            f.writelines(lines)


if __name__ == "__main__":

    test_file = "games/0_0_lines/library/publish_files/books_base.jsonl.zst"
    decompress(test_file, save_output=True)
    print(f"Decompressed file: {test_file}\nNo errors parsing JSON.")
