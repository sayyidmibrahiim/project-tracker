"""CLI Delegate — send prompts to any installed AI CLI and return results.

Usage:
    python cli_delegate.py <provider> "prompt"
    python cli_delegate.py <provider> --model <m> "prompt"
    python cli_delegate.py --list
    python cli_delegate.py --continue <provider> "follow-up"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SESSION_DIR = Path(__file__).parent / ".sessions"
DEFAULT_TIMEOUT = 120

PROVIDERS = {
    "opencode": {
        "bin": "opencode",
        "install": "npm install -g opencode-ai",
        "build": lambda model, prompt, session: (
            ["opencode", "run", "--format", "json"]
            + (["--session", session] if session else [])
            + (["--model", model] if model else [])
            + [prompt]
        ),
        "parse": "ndjson",
        "note": None,
    },
    "mimo": {
        "bin": "mimo",
        "install": "npm install -g @mimo-ai/cli",
        "build": lambda model, prompt, session: (
            ["mimo", "run", "--format", "json"]
            + (["--session", session] if session else [])
            + (["--model", model] if model else [])
            + [prompt]
        ),
        "parse": "ndjson",
        "note": None,
    },
    "claude": {
        "bin": "claude",
        "install": "npm install -g @anthropic-ai/claude-code",
        "build": lambda model, prompt, session: (
            ["claude", "-p", prompt, "--output-format", "json"]
            + (["--model", model] if model else [])
        ),
        "parse": "claude",
        "note": "May hang if Claude Code is already running in this session",
    },
    "gemini": {
        "bin": "gemini",
        "install": "npm install -g @google/gemini-cli",
        "build": lambda model, prompt, session: (
            ["gemini", "-p", prompt, "-o", "json"]
            + (["--model", model] if model else [])
        ),
        "parse": "gemini",
        "note": "Requires active Gemini Code Assist subscription",
    },
    "freebuff": {
        "bin": "freebuff",
        "install": "npm install -g freebuff",
        "build": lambda model, prompt, session: (
            ["freebuff", "-p", prompt]
            + (["--model", model] if model else [])
        ),
        "parse": "raw",
        "note": "Interactive-only; non-interactive mode not supported",
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CLI Delegate")
    p.add_argument("provider", help="CLI provider (opencode, mimo, claude, gemini, freebuff)")
    p.add_argument("prompt", nargs="*", help="Prompt text (quote it)")
    p.add_argument("--model", "-m", help="Model in provider/model format")
    p.add_argument("--list", "-l", action="store_true", help="List available providers")
    p.add_argument(
        "--continue", "-c", nargs="?", const="__last__", default=None,
        dest="continue_session", help="Continue last or specific session"
    )
    p.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--dir", "-d", help="Working directory")
    p.add_argument("--json", action="store_true", help="Raw JSON debug output")
    p.add_argument("--raw", action="store_true", help="Print stdout as-is, no parsing")
    return p.parse_args()


def find_binary(name: str) -> str | None:
    for variant in (name, f"{name}.cmd", f"{name}.exe"):
        found = shutil.which(variant)
        if found:
            return found
    npm_dir = Path(os.environ.get("APPDATA", "")) / "npm"
    for ext in (".cmd", ".exe", ""):
        p = npm_dir / f"{name}{ext}"
        if p.exists():
            return str(p)
    return None


def list_providers():
    print("Available providers:\n")
    for name, cfg in PROVIDERS.items():
        bin_path = find_binary(cfg["bin"])
        status = bin_path if bin_path else "NOT INSTALLED"
        note = f"  ({cfg['note']})" if cfg.get("note") else ""
        print(f"  {name:12s}  {status}{note}")
        print(f"               {cfg['install']}")
    print(f"\nUsage: python cli_delegate.py <provider> [model] \"prompt\"")


def get_session_file(provider: str) -> Path:
    SESSION_DIR.mkdir(exist_ok=True)
    return SESSION_DIR / f"{provider}.last"


def resolve_session(provider: str, continue_arg: str | None) -> str | None:
    if continue_arg and continue_arg != "__last__":
        return continue_arg
    if continue_arg == "__last__":
        sf = get_session_file(provider)
        if sf.exists():
            return sf.read_text().strip()
    return None


# --- Response parsers ---

def parse_ndjson(events: list[dict]) -> tuple[str, str | None]:
    texts, sid = [], None
    for ev in events:
        if ev.get("type") == "text":
            t = ev.get("part", {}).get("text", "")
            if t:
                texts.append(t)
        if "sessionID" in ev:
            sid = ev["sessionID"]
    return "\n".join(texts), sid


def parse_claude(events: list[dict]) -> tuple[str, str | None]:
    texts, sid = [], None
    for ev in events:
        msg = ev.get("message", {})
        if msg.get("role") == "assistant":
            for block in msg.get("content", []):
                if block.get("type") == "text":
                    texts.append(block["text"])
        for key in ("session_id", "sessionId"):
            if key in ev:
                sid = ev[key]
    return "\n".join(texts), sid


def parse_gemini(events: list[dict]) -> tuple[str, str | None]:
    texts = []
    for ev in events:
        for key in ("text", "content"):
            if key in ev:
                texts.append(str(ev[key]))
    return "\n".join(texts), None


PARSERS = {
    "ndjson": parse_ndjson,
    "claude": parse_claude,
    "gemini": parse_gemini,
    "raw": lambda e: ("\n".join(str(x) for x in e), None),
}


def run(args: argparse.Namespace) -> int:
    if args.list:
        list_providers()
        return 0

    provider = args.provider.lower()
    if provider not in PROVIDERS:
        print(f"Unknown provider '{provider}'. Use --list to see options.", file=sys.stderr)
        return 1

    prompt_text = " ".join(args.prompt) if args.prompt else ""
    if not prompt_text:
        print("Error: no prompt provided. Quote your prompt: \"your prompt here\"", file=sys.stderr)
        return 1

    cfg = PROVIDERS[provider]
    model = args.model
    session = resolve_session(provider, args.continue_session)
    cmd = cfg["build"](model, prompt_text, session)

    bin_path = find_binary(cfg["bin"])
    if not bin_path:
        print(f"Error: {provider} not found.\n  Install: {cfg['install']}", file=sys.stderr)
        return 1
    cmd[0] = bin_path

    cwd = args.dir or os.getcwd()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=args.timeout, cwd=cwd
        )
    except FileNotFoundError:
        print(f"Error: failed to run {provider}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print(f"Error: {provider} timed out after {args.timeout}s", file=sys.stderr)
        if cfg.get("note"):
            print(f"  Note: {cfg['note']}", file=sys.stderr)
        return 1

    if result.returncode != 0:
        print(f"{provider} exited with code {result.returncode}", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip()[:500], file=sys.stderr)
        return result.returncode

    stdout = result.stdout.strip()
    if not stdout:
        print(f"Empty response from {provider}", file=sys.stderr)
        return 0

    if args.raw:
        print(stdout)
        return 0

    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"_raw": line})

    if args.json:
        print(json.dumps(events, indent=2))
        return 0

    extractor = PARSERS.get(cfg["parse"], PARSERS["raw"])
    text, session_id = extractor(events)

    if session_id:
        get_session_file(provider).write_text(session_id)

    if text:
        print(text)
    else:
        print(f"No text from {provider}:", file=sys.stderr)
        for ev in events[:3]:
            print(json.dumps(ev, indent=2), file=sys.stderr)
        return 1

    return 0


def main() -> int:
    args = parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
