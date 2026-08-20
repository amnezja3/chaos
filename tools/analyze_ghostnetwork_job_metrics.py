#!/usr/bin/env python3
"""Summarize phase timings emitted by the territory worker's GN jobs."""

import argparse
import ast
import math
import re
import sys
from collections import defaultdict


LINE = re.compile(
    r"\[TERRITORY_WORKER\] ghost_job_id=.*?ok=(?P<ok>\S+) "
    r"elapsed_ms=(?P<elapsed>\d+).*?timings_ms=(?P<timings>\{.*?\}) "
    r"coalesced=(?P<coalesced>\d+)"
)


def percentile(values, fraction):
    values = sorted(values)
    if not values:
        return 0
    return values[min(len(values) - 1, max(0, math.ceil(len(values) * fraction) - 1))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile", nargs="?", help="PM2 worker log; stdin when omitted")
    args = parser.parse_args()
    handle = open(args.logfile, encoding="utf-8", errors="replace") if args.logfile else sys.stdin
    phases = defaultdict(list)
    jobs = 0
    failures = 0
    coalesced = 0
    try:
        for line in handle:
            match = LINE.search(line)
            if not match:
                continue
            jobs += 1
            failures += match.group("ok").lower() not in {"true", "1"}
            coalesced += int(match.group("coalesced"))
            phases["elapsed"].append(int(match.group("elapsed")))
            try:
                timings = ast.literal_eval(match.group("timings"))
            except (SyntaxError, ValueError):
                timings = {}
            for name, value in timings.items():
                if isinstance(value, (int, float)):
                    phases[str(name)].append(int(value))
    finally:
        if args.logfile:
            handle.close()
    print(f"jobs={jobs} failures={failures} coalesced={coalesced}")
    print("phase count p50 p95 max")
    for name, values in sorted(phases.items()):
        print(name, len(values), percentile(values, .50), percentile(values, .95), max(values))


if __name__ == "__main__":
    main()
