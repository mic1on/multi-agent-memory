"""Command-line interface for shared agent memory."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from .config import Settings
from .install import install_agent
from .project import detect_project
from .resources import read_text
from .store import MEMORY_TYPES, Vault

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mam", description="Shared local-first memory for AI agent CLIs")
    parser.add_argument("--config", help="YAML configuration file")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create the Vault layout and search index")
    sub.add_parser("status", help="show Vault and index status")
    for name in ("search", "recall", "context"):
        command = sub.add_parser(name, help=f"{name} confirmed memories")
        command.add_argument("query", nargs="?", default="")
        command.add_argument("--limit", type=int)
        command.add_argument("--include-candidates", action="store_true")
        command.add_argument("--project")
    propose = sub.add_parser("propose", help="write an inert candidate memory")
    propose.add_argument("--file")
    propose.add_argument("--text")
    propose.add_argument("--type", default="learning", choices=tuple(MEMORY_TYPES))
    propose.add_argument("--title")
    propose.add_argument("--scope", default="global")
    propose.add_argument("--project")
    propose.add_argument("--source-session", "--source_session", dest="source_session")
    confirm = sub.add_parser("confirm", help="activate one candidate memory")
    confirm.add_argument("id")
    forget = sub.add_parser("forget", help="deprecate one memory without deleting it")
    forget.add_argument("id")
    sub.add_parser("rebuild-index", help="rebuild SQLite from Markdown")
    summary = sub.add_parser("session-summary", help="save a concise session summary")
    summary.add_argument("--file")
    summary.add_argument("--text")
    summary.add_argument("--title", default="Session summary")
    summary.add_argument("--source-session", "--source_session", dest="source_session")
    pending = sub.add_parser("pending", help="write a crash-recovery receipt")
    pending.add_argument("--session-id", "--session_id", dest="session_id")
    pending.add_argument("--summary")
    pending.add_argument("--summary-file", "--summary_file", dest="summary_file")
    pending.add_argument("--title")
    sub.add_parser("recover", help="promote pending summaries")
    sub.add_parser("protocol", help="print the natural-language agent protocol")
    install = sub.add_parser("install-agent", help="install an agent adapter")
    install.add_argument("--agent", required=True, choices=("auto", "codex", "pi", "opencode", "all"))
    install.add_argument("--force", action="store_true", help="replace a managed adapter after creating a backup")
    install.add_argument("--home", help=argparse.SUPPRESS)
    return parser

def _payload(path: str | None, text: str | None) -> dict[str, Any]:
    if not path:
        return {"body": text or ""}
    raw = Path(path).read_text(encoding="utf-8")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, dict):
        return value
    return {"body": raw}

def _filter_project(rows: list[dict[str, str]], project: str | None) -> list[dict[str, str]]:
    if not project:
        return rows
    return [row for row in rows if row.get("scope") == "global" or row.get("project") == project or project.casefold() in (row.get("body", "") + row.get("title", "")).casefold()]

def _print_rows(rows: list[dict[str, str]], prompt: bool) -> None:
    if prompt:
        print("# Shared memory context")
        if not rows:
            print("No relevant confirmed shared memories were found.")
        for row in rows:
            print(f"\n## {row['title']} [{row['type']}; {row['scope']}]\n{row['body'].strip()}")
        return
    for row in rows:
        excerpt = re.sub(r"\s+", " ", row["body"]).strip()
        print(f"{row['id']}\t{row['status']}\t{row['type']}\t{row['path']}\t{excerpt[:180]}")

def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        vault = Vault(Settings.load(args.config))
        if args.command == "init":
            print(f"initialized {vault.root}; indexed {vault.rebuild()} documents")
        elif args.command == "status":
            print(json.dumps(vault.status(), ensure_ascii=False, indent=2))
        elif args.command in {"search", "recall", "context"}:
            project = args.project
            if args.command == "context" and not project:
                detected = detect_project()
                project = detected[0] if detected else None
            limit = args.limit
            if args.command == "context" and project and limit is None:
                limit = max(vault.settings.recall_limit * 4, 32)
            rows = _filter_project(vault.search(args.query, limit, args.include_candidates), project)
            _print_rows(rows, args.command in {"recall", "context"})
        elif args.command == "propose":
            data = _payload(args.file, args.text)
            for key in ("type", "title", "scope", "project", "source_session"):
                value = getattr(args, key, None)
                if value:
                    data[key] = value
            if data.get("type") == "project" and not data.get("project"):
                detected = detect_project()
                if detected:
                    data["project"] = detected[0]
                    data["scope"] = "project"
            identifier, path = vault.create(data)
            print(f"{identifier}\t{path}")
        elif args.command == "confirm":
            print(vault.confirm(args.id))
        elif args.command == "forget":
            print(f"deprecated\t{vault.forget(args.id)}")
        elif args.command == "rebuild-index":
            print(f"indexed {vault.rebuild()} documents")
        elif args.command == "session-summary":
            if not args.file and not args.text:
                raise ValueError("session-summary requires --file or --text")
            body = args.text if args.text is not None else Path(args.file).read_text(encoding="utf-8")
            identifier, path = vault.create({"type": "session", "title": args.title, "body": body, "source_session": args.source_session or "unknown"}, candidate=False)
            print(f"{identifier}\t{path}")
        elif args.command == "pending":
            summary = args.summary
            if args.summary_file and Path(args.summary_file).is_file():
                summary = Path(args.summary_file).read_text(encoding="utf-8")
            path = vault.pending({"session_id": args.session_id, "summary": summary, "title": args.title})
            print(path or "no summary supplied; nothing saved")
        elif args.command == "recover":
            print(f"recovered {vault.recover()} pending summaries")
        elif args.command == "protocol":
            print(read_text("protocol.md"), end="")
        elif args.command == "install-agent":
            agent = "all" if args.agent == "auto" else args.agent
            home = Path(args.home).expanduser() if args.home else None
            for result in install_agent(agent, force=args.force, home=home):
                print(result)
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"memoryctl: {error}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
