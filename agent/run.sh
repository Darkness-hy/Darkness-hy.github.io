#!/usr/bin/env bash
# Homepage agent — Claude Code harness + DeepSeek v4 Flash + local RAG
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export AGENT_MODEL="${AGENT_MODEL:-deepseek-v4-flash}"
export AGENT_EFFORT="${AGENT_EFFORT:-low}"
export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-https://api.deepseek.com/anthropic}"
export PORT="${PORT:-8788}"

if [[ -z "${DEEPSEEK_API_KEY:-}" && -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Set DEEPSEEK_API_KEY (or ANTHROPIC_API_KEY) in agent/.env" >&2
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "claude CLI not found in PATH" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/uvicorn server:app --host 0.0.0.0 --port "$PORT"
