#!/usr/bin/env python3
import re
from pathlib import Path
from collections import defaultdict

DOWNLOAD_DIR = Path(__file__).parent / "downloads"
PATTERN = re.compile(r"^(?P<customer>[A-Za-z0-9-]+)-(?P<doc>[A-Za-z0-9-]+)-(?P<ts>\d{8}T\d{6}Z)-.+\.pdf$")

def keep_only_latest_per_customer(download_dir: Path = DOWNLOAD_DIR) -> int:
    groups = defaultdict(list)
    for p in download_dir.glob("*.pdf"):
        m = PATTERN.match(p.name)
        if not m:
            continue
        cust = m.group("customer")
        groups[cust].append(p)

    removed = 0
    for cust, files in groups.items():
        if len(files) <= 1:
            continue
        files_sorted = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)
        for old in files_sorted[1:]:
            try:
                old.unlink()
                removed += 1
            except Exception:
                pass
    return removed

if __name__ == "__main__":
    DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)
    removed = keep_only_latest_per_customer(DOWNLOAD_DIR)
    print(f"Removed {removed} old files")
