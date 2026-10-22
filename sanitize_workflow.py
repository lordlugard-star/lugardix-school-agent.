#!/usr/bin/env python3
"""Sanitize n8n workflow exports and scan for leaked secrets or personal data.

Standard library only.

  Sanitize:  python scripts/sanitize_workflow.py workflows/raw workflows [--redact TEXT ...]
  Check:     python scripts/sanitize_workflow.py --check workflows

Sanitizing removes credential ids and names, instance and webhook ids, pinned
test data, and masks emails, phone numbers or chat ids, tokens, JWTs and
Supabase project URLs. Always read the output yourself before committing.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PATTERNS = [
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), "<REDACTED_JWT>"),
    ("bearer_token", re.compile(r"(?i)\bBearer\s+(?!<REDACTED>)[A-Za-z0-9._~+/=-]{16,}"), "Bearer <REDACTED>"),
    ("telegram_bot_token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}\b"), "<REDACTED_BOT_TOKEN>"),
    ("api_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "<REDACTED_API_KEY>"),
    ("supabase_url", re.compile(r"https://(?!<)[a-z0-9]{20}\.supabase\.co"), "https://<PROJECT_REF>.supabase.co"),
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|test)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "user@example.com"),
    ("phone_or_chat_id", re.compile(r"(?<![\w.:/-])\+?\d{9,20}(?![\w.-])"), "<PHONE_OR_ID>"),
]

DROP_TOP_LEVEL = {
    "id", "versionId", "activeVersionId", "activeVersion", "pinData", "staticData",
    "meta", "shared", "tags", "triggerCount", "isArchived", "active",
    "createdAt", "updatedAt", "homeProject",
}


def scrub(text, extra):
    for _, rx, repl in PATTERNS:
        text = rx.sub(repl, text)
    for word in extra:
        text = re.sub(re.escape(word), "REDACTED", text, flags=re.IGNORECASE)
    return text


def walk(node, fn):
    if isinstance(node, dict):
        return {(fn(k) if isinstance(k, str) else k): walk(v, fn) for k, v in node.items()}
    if isinstance(node, list):
        return [walk(v, fn) for v in node]
    if isinstance(node, str):
        return fn(node)
    return node


def clean_workflow(wf, extra):
    wf = {k: v for k, v in wf.items() if k not in DROP_TOP_LEVEL}
    for n in wf.get("nodes", []):
        n.pop("webhookId", None)
        creds = n.get("credentials")
        if isinstance(creds, dict):
            n["credentials"] = {t: {"id": "REPLACE_ME", "name": t} for t in creds}
        wid = (n.get("parameters") or {}).get("workflowId")
        if isinstance(wid, dict) and "value" in wid:
            wid["value"] = "REPLACE_ME"
    settings = wf.get("settings")
    if isinstance(settings, dict) and "errorWorkflow" in settings:
        settings["errorWorkflow"] = "REPLACE_ME"
    return walk(wf, lambda s: scrub(s, extra))


def strings(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str):
                yield k
            yield from strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from strings(v)
    elif isinstance(node, str):
        yield node


def check_file(path):
    problems = []
    try:
        wf = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid JSON: {exc}"]
    if isinstance(wf, dict):
        if "pinData" in wf:
            problems.append("pinData present (pinned test data)")
        for n in wf.get("nodes", []):
            for t, c in (n.get("credentials") or {}).items():
                if isinstance(c, dict) and c.get("id") not in (None, "REPLACE_ME"):
                    problems.append(f"credential id not placeholder on node '{n.get('name')}' ({t})")
    for s in strings(wf):
        for label, rx, _ in PATTERNS:
            m = rx.search(s)
            if m:
                shown = m.group(0)
                shown = shown[:3] + "..." + shown[-2:] if len(shown) > 8 else "***"
                problems.append(f"{label} found: {shown}")
    return problems


def json_files(p):
    p = Path(p)
    return [p] if p.is_file() else sorted(p.rglob("*.json"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--check", action="store_true", help="scan only; exit 1 if anything suspicious is found")
    ap.add_argument("--redact", action="append", default=[], help="extra text to mask (case-insensitive); repeatable")
    args = ap.parse_args()

    files = [f for f in json_files(args.input) if "raw" not in f.parts]
    if args.check:
        if not files:
            print("No workflow JSON files to check.")
            return 0
        failed = False
        for f in files:
            problems = check_file(f)
            if problems:
                failed = True
                print(f"FAIL {f}")
                for p in problems:
                    print(f"   - {p}")
            else:
                print(f"ok   {f}")
        return 1 if failed else 0

    if not args.output:
        ap.error("output directory required when not using --check")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    src = [f for f in json_files(args.input)]
    if not src:
        print("No JSON files found in", args.input)
        return 1
    for f in src:
        wf = json.loads(f.read_text(encoding="utf-8"))
        cleaned = clean_workflow(wf, args.redact)
        dest = out / f.name
        dest.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"sanitized {f} -> {dest}")
    print("Now run with --check, then READ the files before committing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
