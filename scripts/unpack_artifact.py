"""Распаковать Anthropic Artifacts standalone bundle (manifest+template, gzip+base64).

Usage:
    python scripts/unpack_artifact.py <input.html> <output_dir>
"""

from __future__ import annotations

import base64
import gzip
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)

    html = src.read_text(encoding="utf-8")

    manifest_match = re.search(
        r'<script[^>]*type="__bundler/manifest"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    template_match = re.search(
        r'<script[^>]*type="__bundler/template"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not manifest_match or not template_match:
        print("ERROR: bundler tags not found")
        return 1

    manifest = json.loads(manifest_match.group(1))
    template_raw = template_match.group(1).strip()
    try:
        template = json.loads(template_raw)
    except json.JSONDecodeError:
        template = template_raw

    by_path: dict[str, dict[str, object]] = {}
    for uuid, entry in manifest.items():
        binary = base64.b64decode(entry["data"])
        if entry.get("compressed"):
            binary = gzip.decompress(binary)
        path = entry.get("path") or entry.get("name") or uuid
        by_path[path] = {
            "uuid": uuid,
            "mime": entry.get("mime"),
            "bytes": binary,
        }

    (dst / "_manifest_paths.txt").write_text(
        "\n".join(sorted(by_path.keys())) + "\n",
        encoding="utf-8",
    )
    if isinstance(template, str):
        (dst / "_template.txt").write_text(template, encoding="utf-8")
    else:
        (dst / "_template.json").write_text(
            json.dumps(template, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    for path, blob in by_path.items():
        target = dst / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob["bytes"])  # type: ignore[arg-type]

    print(f"Unpacked {len(by_path)} files to {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
