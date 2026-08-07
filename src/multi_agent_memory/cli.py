"""Command-line interface for shared agent memory."""
from __future__ import annotations
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

try:
    import termios
    import tty
except ImportError:  # pragma: no cover - Windows uses the non-interactive form.
    termios = None
    tty = None
from . import __version__
from .config import Settings
from .install import adapter_status, install_agent, sync_adapters
from .project import detect_project
from .resources import read_text
from .store import MEMORY_TYPES, Vault

def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mam", description="Shared local-first memory for AI agent CLIs")
    parser.add_argument("-v", "--version", action="version", version=__version__)
    parser.add_argument("--config", help="YAML configuration file")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("version", help="show the installed mam version")
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
    install = sub.add_parser("install", help="install one or more agent adapters")
    install.add_argument("--agent", action="append", choices=("codex", "pi", "opencode", "claude"), help="adapter to install; repeat to select multiple")
    install.add_argument("--all", action="store_true", help="install all supported adapters")
    install.add_argument("--force", action="store_true", help="replace a managed adapter after creating a backup")
    install.add_argument("--home", help=argparse.SUPPRESS)
    legacy = sub.add_parser("install-agent", help="compatibility alias for install")
    legacy.add_argument("--agent", required=True, choices=("auto", "codex", "pi", "opencode", "claude", "all"))
    legacy.add_argument("--force", action="store_true", help="replace a managed adapter after creating a backup")
    legacy.add_argument("--home", help=argparse.SUPPRESS)
    return parser


SUPPORTED_AGENTS = ("codex", "pi", "opencode", "claude")


def _interactive_agents() -> list[str]:
    """Select adapters without adding a third-party terminal dependency."""

    if termios is None or tty is None or not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("mam install needs an interactive terminal; use --agent NAME or --all")
    selected: set[str] = set()
    cursor = 0
    options = ("codex", "pi", "opencode", "claude", "all")
    print("Select agent adapters (Up/Down, Space, Enter):")
    old_settings = termios.tcgetattr(sys.stdin.fileno())
    try:
        tty.setcbreak(sys.stdin.fileno())
        while True:
            print("\x1b[2J\x1b[H", end="")
            print("Select agent adapters (Up/Down, Space, Enter):")
            for index, option in enumerate(options):
                marker = "x" if option in selected or (option == "all" and len(selected) == len(SUPPORTED_AGENTS)) else " "
                pointer = ">" if index == cursor else " "
                print(f" {pointer} [{marker}] {option}")
            key = sys.stdin.read(1)
            if key == "\x1b":
                sequence = sys.stdin.read(2)
                if sequence == "[A":
                    cursor = (cursor - 1) % len(options)
                elif sequence == "[B":
                    cursor = (cursor + 1) % len(options)
            elif key == " ":
                if options[cursor] == "all":
                    selected = set(SUPPORTED_AGENTS) if len(selected) != len(SUPPORTED_AGENTS) else set()
                elif options[cursor] in selected:
                    selected.remove(options[cursor])
                else:
                    selected.add(options[cursor])
            elif key in ("\r", "\n"):
                if selected:
                    return list(SUPPORTED_AGENTS if len(selected) == len(SUPPORTED_AGENTS) else (agent for agent in SUPPORTED_AGENTS if agent in selected))
                print("Select at least one adapter.")
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)


def _selected_agents(args: argparse.Namespace) -> list[str]:
    if args.command == "install-agent":
        return list(SUPPORTED_AGENTS) if args.agent == "all" or args.agent == "auto" else [args.agent]
    if args.all:
        return list(SUPPORTED_AGENTS)
    if args.agent:
        return list(dict.fromkeys(args.agent))
    return _interactive_agents()

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
    if args.command == "version":
        print(__version__)
        return 0
    try:
        vault = Vault(Settings.load(args.config))
        if args.command == "init":
            print(f"initialized {vault.root}; indexed {vault.rebuild()} documents")
        elif args.command == "status":
            status = vault.status()
            adapter_info = adapter_status(state_dir=vault.settings.state_dir)
            status["adapters"] = adapter_info["adapters"]
            status["adapter_manifest"] = adapter_info["manifest"]
            if "error" in adapter_info:
                status["adapter_error"] = adapter_info["error"]
            print(json.dumps(status, ensure_ascii=False, indent=2))
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
            recovered = vault.recover()
            if vault.settings.auto_sync_adapters:
                try:
                    sync_adapters(state_dir=vault.settings.state_dir)
                except (OSError, ValueError, TypeError, sqlite3.Error):
                    pass
            print(f"recovered {recovered} pending summaries")
        elif args.command == "protocol":
            print(read_text("protocol.md"), end="")
        elif args.command in {"install", "install-agent"}:
            home = Path(args.home).expanduser() if args.home else None
            for agent in _selected_agents(args):
                for result in install_agent(agent, force=args.force, home=home, state_dir=vault.settings.state_dir):
                    print(result)
        return 0
    except (OSError, ValueError, TypeError, sqlite3.Error) as error:
        print(f"memoryctl: {error}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
