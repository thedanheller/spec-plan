#!/usr/bin/env python3
"""Match the acceptance scenarios of an sp Build Plan to test names.

Deterministic layer-1 check for /sp:verify. Standard library only.

    match_scenarios.py PLAN --junit REPORT.xml [--junit ...]
    match_scenarios.py PLAN --names NAMES.txt     # lines: PASS|FAIL|SKIP<TAB>full test name
    match_scenarios.py PLAN --scan PATH [PATH ...] # static scan of test sources

A scenario is a bullet under a task's "Scenarios:" line:

    - [REF] WHEN <condition>, THEN <outcome> (pending: <item>)

where the [REF] prefix and the pending suffix are optional. A test matches a
scenario when its full name contains the scenario text (WHEN to the end of the
outcome) and, when present, the rule reference. Both sides are compared after
the same normalization, so formatting differences don't matter: letter case,
accents, HTML entities, punctuation, underscores, camelCase and spacing are all
ignored.

Prints JSON to stdout. Unmatched scenarios are reported, never dropped.
"""

import argparse
import html
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

BULLET = re.compile(r"^\s*[-*+]\s+(?P<body>.*\S)\s*$")
SCENARIOS_HEADER = re.compile(r"^\s*(?:[-*+]\s+)?\**Scenarios:?\**:?\s*$", re.IGNORECASE)
TASK = re.compile(r"^(?P<num>\d+)[.)]\s")
SCENARIO = re.compile(
    r"^(?:\[(?P<ref>[^\]]+)\]\s*)?"
    r"(?P<text>WHEN\b.*?)"
    r"(?:\s*\(\s*pending:\s*(?P<pending>.*)\))?\s*$",
    re.IGNORECASE,
)
SKIP_DIRS = {".git", "node_modules", "change-requests", "vendor", "dist", "build",
             "target", ".venv", "venv", "__pycache__", ".next", "coverage"}
MAX_SCAN_BYTES = 2_000_000


def strip_accents(s):
    # Some reporters escape test names more than once (Node's JUnit reporter
    # writes `"` as `&amp;quot;`), so decode entities until nothing changes.
    while True:
        decoded = html.unescape(s)
        if decoded == s:
            break
        s = decoded
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def tokens(s):
    """Words of s: camelCase and letter/digit boundaries split, case folded."""
    s = strip_accents(s)
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s)
    s = re.sub(r"(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])", " ", s)
    return [t for t in re.split(r"[\W_]+", s.casefold()) if t]


def squash(s):
    """s with everything but letters and digits removed, case folded."""
    return "".join(t for t in re.split(r"[\W_]+", strip_accents(s).casefold()) if t)


def contains_ref(name_tokens, ref):
    hay = " " + " ".join(name_tokens) + " "
    return (" " + " ".join(tokens(ref)) + " ") in hay


def parse_plan(path):
    scenarios, malformed = [], []
    task = None
    in_block = False
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.rstrip("\n")
            m = TASK.match(line)
            if m:
                task, in_block = m.group("num"), False
                continue
            if line.startswith("#"):
                task, in_block = None, False
                continue
            if SCENARIOS_HEADER.match(line):
                in_block = True
                continue
            if not in_block:
                continue
            if not line.strip():
                continue
            b = BULLET.match(line)
            if not b:
                in_block = False
                continue
            body = b.group("body").replace("**", "").replace("`", "").strip()
            s = SCENARIO.match(body)
            if not s:
                malformed.append({"line": lineno, "task": task, "text": body})
                continue
            scenarios.append({
                "line": lineno,
                "task": task,
                "ref": (s.group("ref") or "").strip() or None,
                "text": s.group("text").strip(),
                "pending": (s.group("pending") or "").strip() or None,
            })
    return scenarios, malformed


def tests_from_junit(paths):
    tests = []

    def walk(node, prefix):
        tag = node.tag.split("}")[-1]
        if tag == "testcase":
            parts = prefix + [node.get("classname") or "", node.get("name") or ""]
            status = "PASS"
            for child in node:
                ctag = child.tag.split("}")[-1]
                if ctag in ("failure", "error"):
                    status = "FAIL"
                    break
                if ctag == "skipped":
                    status = "SKIP"
            tests.append({"name": " ".join(p for p in parts if p), "status": status})
            return
        if tag == "testsuite":
            prefix = prefix + [node.get("name") or ""]
        for child in node:
            walk(child, prefix)

    for p in paths:
        walk(ET.parse(p).getroot(), [])
    return tests


def tests_from_names(path):
    tests = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            status, sep, name = line.partition("\t")
            if sep and status.strip().upper() in ("PASS", "FAIL", "SKIP"):
                tests.append({"name": name.strip(), "status": status.strip().upper()})
            else:
                tests.append({"name": line.strip(), "status": "UNKNOWN"})
    return tests


def scan_files(paths):
    files = []
    for root in paths:
        if os.path.isfile(root):
            files.append(root)
            continue
        for d, dirs, names in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            files.extend(os.path.join(d, n) for n in names)
    out = []
    for p in sorted(set(files)):
        try:
            if os.path.getsize(p) > MAX_SCAN_BYTES:
                continue
            with open(p, encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        out.append({"name": p, "status": "UNKNOWN", "_content": text})
    return out


def match(scenarios, tests, scan):
    prepared = []
    for t in tests:
        body = t.get("_content", t["name"])
        prepared.append((t, squash(body), tokens(body), set(tokens(t["name"]))))

    results = []
    for s in scenarios:
        needle = squash(s["text"])
        matches = []
        for t, sq, tk, _ in prepared:
            if needle and needle in sq and (not s["ref"] or contains_ref(tk, s["ref"])):
                matches.append({"name": t["name"], "status": t["status"]})
        statuses = {m["status"] for m in matches}
        if not matches:
            passes = None
        elif "FAIL" in statuses:
            passes = "no"
        elif statuses == {"PASS"}:
            passes = "yes"
        elif statuses <= {"SKIP"}:
            passes = "skipped"
        elif "UNKNOWN" in statuses:
            passes = "unknown"
        else:
            passes = "partly skipped"
        r = dict(s)
        r["coverage"] = "pending" if s["pending"] else ("covered" if matches else "uncovered")
        r["passes"] = passes
        r["tests"] = matches
        if not matches and not s["pending"] and prepared:
            want = set(tokens(((s["ref"] or "") + " " + s["text"])))
            best, score = None, 0.0
            for t, _, tk, name_tokens in prepared:
                words = set(tk) if scan else name_tokens
                overlap = len(want & words) / len(want) if want else 0.0
                if overlap > score:
                    best, score = t["name"], overlap
            if best and score >= 0.5:
                r["hint"] = {"closest": best, "shared_words": round(score, 2),
                             "note": "a hint, not a match"}
        results.append(r)
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("plan")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--junit", action="append", metavar="XML")
    src.add_argument("--names", metavar="FILE")
    src.add_argument("--scan", nargs="+", metavar="PATH")
    args = ap.parse_args()

    scenarios, malformed = parse_plan(args.plan)
    if args.junit:
        tests, source = tests_from_junit(args.junit), "junit"
    elif args.names:
        tests, source = tests_from_names(args.names), "names"
    else:
        tests, source = scan_files(args.scan), "scan"

    results = match(scenarios, tests, source == "scan")
    count = lambda k, v: sum(1 for r in results if r[k] == v)
    json.dump({
        "plan": args.plan,
        "source": source,
        "tests_seen": len(tests),
        "summary": {
            "scenarios": len(results),
            "covered": count("coverage", "covered"),
            "uncovered": count("coverage", "uncovered"),
            "pending": count("coverage", "pending"),
            "failing": count("passes", "no"),
            "malformed": len(malformed),
        },
        "scenarios": results,
        "malformed": malformed,
    }, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
