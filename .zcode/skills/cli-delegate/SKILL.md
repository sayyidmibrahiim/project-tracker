---
name: cli-delegate
description: Delegate prompts to any installed AI CLI (opencode, mimo, claude, gemini, freebuff). Use when user says "delegate to", "ask mimo", "ask opencode", or invokes /delegate-to-another-cli.
user-invocable: true
allowed-tools:
  - Bash(python .claude/skills/cli-delegate/cli_delegate.py*)
  - Bash(D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe .claude/skills/cli-delegate/cli_delegate.py*)
---

# CLI Delegate

Send prompts to any installed AI CLI tool and inject results back into Claude Code context.

## When to use

- User says "delegate to <provider>", "ask <provider>", or invokes `/delegate-to-another-cli`
- User wants a second opinion from a different AI model
- User wants to compare answers across providers

## Supported providers

| Provider  | Status          | Install                                  |
| --------- | --------------- | ---------------------------------------- |
| opencode  | works           | `npm install -g opencode-ai`             |
| mimo      | works           | `npm install -g @mimo-ai/cli`            |
| claude    | may hang*       | `npm install -g @anthropic-ai/claude-code` |
| gemini    | auth required** | `npm install -g @google/gemini-cli`      |
| freebuff  | interactive***  | `npm install -g freebuff`                |

\* May hang if Claude Code is already running in this session
\** Requires active Gemini Code Assist subscription
\*** FreeBuff is interactive-only, non-interactive mode not supported

## Usage

```
/delegate-to-another-cli <provider> "prompt"
```

### Examples

```
/delegate-to-another-cli opencode "review my auth module"
/delegate-to-another-cli mimo "explain monads in Go"
/delegate-to-another-cli opencode --model deepseek-v4-flash-free "what's the best way to handle errors?"
```

### Session continuation

Providers that support sessions (opencode, mimo) can resume context:

```
/delegate-to-another-cli opencode --continue "what did I just ask?"
/delegate-to-another-cli mimo --continue "follow up on that"
```

### List available providers

```
/delegate-to-another-cli --list
```

## Execution

Run from repo root using the project venv Python:

```
D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe .claude/skills/cli-delegate/cli_delegate.py <provider> "prompt"
```

### Options

- `--list` — show available providers and install status
- `--model <provider/model>` — override the default model
- `--continue [session_id]` — resume last session or specific session
- `--timeout <seconds>` — override default 120s timeout
- `--dir <path>` — set working directory
- `--json` — return raw JSON events for debugging
- `--raw` — skip JSON parsing, print stdout as-is

## Error handling

- Provider not installed → shows install command
- Timeout → reports timeout with suggestion
- Non-zero exit → shows stderr output
- No text in response → shows raw events for debugging

## Do NOT

- Do not auto-trigger — only invoke when user explicitly asks
- Do not chain multiple providers without user requesting it
- Do not modify the provider's response before displaying
