#!/usr/bin/env python3
"""Summarize opt-in [DB_LOCK] runtime lines from a PM2 log file or stdin."""

import argparse
import math
import re
import sys
from collections import defaultdict


LINE = re.compile(
    r"\[DB_LOCK\].*?origin=(?P<origin>\S+).*?outcome=(?P<outcome>\S+)"
    r".*?wait_ms=(?P<wait>\d+).*?hold_ms=(?P<hold>\d+)"
    r".*?commit_ms=(?P<commit>\d+).*?statements=(?P<statements>\d+)"
)


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return 0
    return values[min(len(values) - 1, max(0, math.ceil(len(values) * fraction) - 1))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile", nargs="-", help="PM2 log; stdin when omitted")
    args = parser.parse_args()
    handle = open(args.logfile, encoding="utf-8", errors="replace") if args.logfile else sys.stdin
    grouped = defaultdict(list)
    try:
        for line in handle:
            match = LINE.search(line)
            if match:
                grouped[match.group("origin")].append({
                    key: int(match.group(key))
                    for key in ("wait", "hold", "commit", "statements")
                })
    finally:
        if args.logfile:
            handle.close()
    print("origin count wait_p50 wait_p95 wait_max hold_p50 hold_p95 hold_max")
    for origin, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        waits = [row["wait"] for row in rows]
        holds = [row["hold"] for row in rows]
        print(
            origin, len(rows), percentile(waits, .50), percentile(waits, .95), max(waits),
            percentile(holds, .50), percentile(holds, .95), max(holds),
        )


if __name__ == "__main__":
    main()
