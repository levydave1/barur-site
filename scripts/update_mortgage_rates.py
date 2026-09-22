#!/usr/bin/env python3
"""
Fetches the Bank of Israel's published average mortgage interest rates and
writes them to market-rates.json at the repo root, for check.html to read
at runtime instead of using hard-coded numbers.

Sources (public, no auth required, updated monthly by the Bank of Israel):
  - Linked (tsamud) mortgages:      https://www.boi.org.il/boi_files/Pikuah/pribmash.xls
  - Non-linked shekel mortgages:    https://www.boi.org.il/boi_files/Pikuah/mashfix.xls

The exact column layout of these files was not verified in advance (the
build environment that wrote this script had no network access to them).
This script is defensive: it looks for the last row that has both a date
and a plausible interest-rate number (0.5-15%), and only writes the output
file if it found sane values in both sources. If the layout doesn't match
on the first real run, check the workflow's Action log, inspect the two
files directly, and adjust EXPECTED_SHEET / column selection below.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

LINKED_URL = "https://www.boi.org.il/boi_files/Pikuah/pribmash.xls"
UNLINKED_URL = "https://www.boi.org.il/boi_files/Pikuah/mashfix.xls"
OUT_PATH = Path(__file__).resolve().parent.parent / "market-rates.json"

MIN_PLAUSIBLE_RATE = 0.5
MAX_PLAUSIBLE_RATE = 15.0

# Fallback values used only if a fetch fails outright (keeps the site working).
FALLBACK = {"low": 3.65, "mid": 4.3, "high": 5.35}


def fetch_xls(url: str) -> bytes:
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.content


def last_plausible_rate(xls_bytes: bytes) -> float | None:
    """Read every sheet, walk rows bottom-up, and return the first numeric
    value found that looks like a plausible annual interest rate (%)."""
    try:
        sheets = pd.read_excel(pd.io.common.BytesIO(xls_bytes), sheet_name=None, header=None)
    except Exception as e:
        print(f"  failed to parse workbook: {e}", file=sys.stderr)
        return None

    for sheet_name, df in sheets.items():
        # Walk from the bottom (most recent data is usually last) upward.
        for row_idx in range(len(df) - 1, -1, -1):
            row = df.iloc[row_idx]
            for val in row:
                try:
                    num = float(val)
                except (TypeError, ValueError):
                    continue
                if MIN_PLAUSIBLE_RATE <= num <= MAX_PLAUSIBLE_RATE:
                    print(f"  sheet '{sheet_name}' row {row_idx}: candidate rate {num}")
                    return round(num, 2)
    return None


def main():
    result = dict(FALLBACK)
    result["source"] = "fallback"
    ok = True

    print("Fetching linked-mortgage rate file...")
    try:
        linked_bytes = fetch_xls(LINKED_URL)
        linked_rate = last_plausible_rate(linked_bytes)
    except Exception as e:
        print(f"  fetch failed: {e}", file=sys.stderr)
        linked_rate = None

    print("Fetching unlinked-mortgage rate file...")
    try:
        unlinked_bytes = fetch_xls(UNLINKED_URL)
        unlinked_rate = last_plausible_rate(unlinked_bytes)
    except Exception as e:
        print(f"  fetch failed: {e}", file=sys.stderr)
        unlinked_rate = None

    if linked_rate is None or unlinked_rate is None:
        print("Could not extract a plausible rate from one or both sources; keeping previous file.", file=sys.stderr)
        ok = False
    else:
        low = min(linked_rate, unlinked_rate)
        mid = unlinked_rate
        high = round(max(linked_rate, unlinked_rate) + 1.0, 2)
        result = {
            "low": low,
            "mid": mid,
            "high": high,
            "linkedRate": linked_rate,
            "unlinkedRate": unlinked_rate,
            "source": "boi.org.il (linked + unlinked mortgage rate files)",
        }

    result["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not ok:
        # Don't overwrite a good file with fallback numbers; exit non-zero so
        # the Action shows a failed/attention-needed run instead of silently
        # reverting to placeholder data.
        print("Exiting without writing market-rates.json (extraction failed).", file=sys.stderr)
        sys.exit(1)

    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH}: {result}")


if __name__ == "__main__":
    main()

