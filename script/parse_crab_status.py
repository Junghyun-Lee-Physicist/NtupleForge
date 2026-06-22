#!/usr/bin/env python3
# parse_crab_status.py
#
# Parse a saved `crab status` log into a per-task summary, and optionally dump
# the raw status lines (absorbs the old checkCrabstatusCommand.txt grep recipes).
#
# Usage examples:
#   python3 script/parse_crab_status.py crab_status.log
#   cat crab_status.log | python3 script/parse_crab_status.py -
#
# Optional:
#   python3 script/parse_crab_status.py crab_status.log --complete-statuses finished transferred
#   python3 script/parse_crab_status.py crab_status.log --show-lines
#   python3 script/parse_crab_status.py crab_status.log --show-lines --status-keywords running failed
#   python3 script/parse_crab_status.py crab_status.log --json out.json

from __future__ import annotations
import argparse
import json
import re
import sys
from collections import defaultdict, OrderedDict

TASK_START_RE = re.compile(r"^\[(?P<task>[^\]]+)\]\s+Processing\.\.\.\s*$")
JOBS_STATUS_HEADER_RE = re.compile(r"^\s*Jobs status:\s*$")

# Example lines:
#   failed       		  1.7% (  5/297)
#   running      		 98.3% (292/297)
#   transferring            0.3% (  1/297)
STATUS_LINE_RE = re.compile(
    r"^\s*(?P<status>[A-Za-z0-9_]+)\s+.*?\(\s*(?P<n>\d+)\s*/\s*(?P<tot>\d+)\s*\)\s*$"
)

def parse_tasks(lines: list[str]) -> dict[str, dict]:
    """
    Returns:
      {
        task_name: {
          "statuses": {status: count, ...},
          "total": int|None,
          "has_requestcache_error": bool,
        },
        ...
      }
    """
    tasks: dict[str, dict] = OrderedDict()
    current_task: str | None = None
    in_jobs_block = False

    for line in lines:
        line = line.rstrip("\n")

        m = TASK_START_RE.match(line)
        if m:
            current_task = m.group("task")
            tasks.setdefault(current_task, {"statuses": defaultdict(int), "total": None, "has_requestcache_error": False})
            in_jobs_block = False
            continue

        # Mark requestcache issue inside a task block
        if current_task is not None and ".requestcache" in line and "Cannot find" in line:
            tasks[current_task]["has_requestcache_error"] = True

        if current_task is None:
            continue

        if JOBS_STATUS_HEADER_RE.match(line):
            in_jobs_block = True
            continue

        if in_jobs_block:
            sm = STATUS_LINE_RE.match(line)
            if sm:
                status = sm.group("status")
                n = int(sm.group("n"))
                tot = int(sm.group("tot"))
                tasks[current_task]["statuses"][status] += n
                # total should be consistent across lines; keep the max just in case
                if tasks[current_task]["total"] is None:
                    tasks[current_task]["total"] = tot
                else:
                    tasks[current_task]["total"] = max(tasks[current_task]["total"], tot)
                continue
            else:
                # End of status block when we hit a non-matching line (blank, "No publication...", etc.)
                if line.strip() == "" or line.lstrip().startswith("No publication") or line.lstrip().startswith("Error Summary"):
                    in_jobs_block = False

    # Convert defaultdict -> dict for clean output
    for t in tasks:
        tasks[t]["statuses"] = dict(tasks[t]["statuses"])
    return tasks

def fmt_int(x: int | None) -> str:
    return "-" if x is None else str(x)

def grep_status_lines(lines: list[str], keywords: list[str]) -> "OrderedDict[str, list[str]]":
    """Return matching raw log lines grouped by keyword (case-insensitive).

    Replaces the manual ``grep running crab_status.log`` / ``grep failed ...``
    recipes from the old checkCrabstatusCommand.txt: a single pass collects the
    lines for every keyword so the report can show them inline.
    """
    out: "OrderedDict[str, list[str]]" = OrderedDict((k, []) for k in keywords)
    lowered = [(k, k.lower()) for k in keywords]
    for raw in lines:
        line = raw.rstrip("\n")
        ll = line.lower()
        for k, kl in lowered:
            if kl in ll:
                out[k].append(line.strip())
    return out

def main():
    ap = argparse.ArgumentParser(description="Parse CRAB 'status' output log and summarize job states.")
    ap.add_argument("logfile", help="Path to crab status log file, or '-' for stdin")
    ap.add_argument("--complete-statuses", nargs="+", default=["finished"],
                    help="Which statuses count as 'complete' (default: finished). Example: --complete-statuses finished transferred")
    ap.add_argument("--json", dest="json_out", default=None, help="Write full parsed result to a JSON file")
    ap.add_argument("--show-lines", action="store_true",
                    help="Also print the raw log lines matching the status keywords, grouped "
                         "by keyword. Absorbs the old checkCrabstatusCommand.txt grep recipes "
                         "(grep running/transferring/failed/finished ...) into one report.")
    ap.add_argument("--status-keywords", nargs="+",
                    default=["running", "transferring", "failed", "finished"],
                    help="Keywords scanned by --show-lines (default: running transferring "
                         "failed finished).")
    args = ap.parse_args()

    if args.logfile == "-":
        content = sys.stdin.read().splitlines(True)
    else:
        with open(args.logfile, "r", encoding="utf-8", errors="replace") as f:
            content = f.readlines()

    tasks = parse_tasks(content)

    # Build per-task summary
    complete_keys = set(args.complete_statuses)
    per_task_rows = []
    grand = defaultdict(int)

    for task, info in tasks.items():
        statuses = info["statuses"]
        total = info["total"]
        failed = statuses.get("failed", 0)
        running = statuses.get("running", 0)
        complete = sum(statuses.get(k, 0) for k in complete_keys)

        # Aggregate all statuses as well
        for st, cnt in statuses.items():
            grand[st] += cnt
        if total is not None:
            grand["__TOTAL__"] += total

        per_task_rows.append((task, total, failed, complete, running, info["has_requestcache_error"], statuses))

    # Print a readable summary
    print("=" * 100)
    print("CRAB status summary (parsed)")
    print("=" * 100)
    print(f"Complete counted as: {', '.join(args.complete_statuses)}")
    print()

    # Header
    print(f"{'TASK':<28} {'TOTAL':>6} {'FAILED':>6} {'COMP':>6} {'RUN':>6} {'REQCACHE?':>9}")
    print("-" * 100)

    for (task, total, failed, comp, run, reqerr, statuses) in per_task_rows:
        print(f"{task:<28} {fmt_int(total):>6} {failed:>6} {comp:>6} {run:>6} {('YES' if reqerr else 'no'):>9}")

    print("-" * 100)

    # Grand totals (status-wise)
    grand_total = grand.get("__TOTAL__", 0)
    grand_failed = grand.get("failed", 0)
    grand_running = grand.get("running", 0)
    grand_complete = sum(grand.get(k, 0) for k in complete_keys)

    print(f"{'ALL TASKS':<28} {grand_total:>6} {grand_failed:>6} {grand_complete:>6} {grand_running:>6} {'':>9}")
    print()

    # Also show all status keys found
    status_keys = sorted([k for k in grand.keys() if k != "__TOTAL__"])
    print("Statuses observed (sum over tasks):")
    for k in status_keys:
        print(f"  - {k:>14}: {grand[k]}")
    print()

    # Raw matching lines (absorbs checkCrabstatusCommand.txt). Off by default
    # to keep the summary clean on large logs; enable with --show-lines.
    if args.show_lines:
        grouped = grep_status_lines(content, args.status_keywords)
        print("=" * 100)
        print(f"Raw lines matching keywords: {', '.join(args.status_keywords)}")
        print("=" * 100)
        for kw, matched in grouped.items():
            print(f"\n[{kw}]  ({len(matched)} line(s))")
            print("-" * 100)
            for ln in matched:
                print(f"  {ln}")
        print()

    if args.json_out:
        out = {
            "complete_statuses": args.complete_statuses,
            "tasks": tasks,
            "grand": dict(grand),
        }
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, sort_keys=False)
        print(f"[OK] Wrote JSON: {args.json_out}")

if __name__ == "__main__":
    main()
