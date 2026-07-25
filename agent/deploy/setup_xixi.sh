#!/usr/bin/env bash
# Create isolated system user `xixi` for the homepage agent (茜茜).
# Hardens: no model local FS tools, readonly knowledge, secrets outside knowledge,
# logs without full prompts by default.
#
# Usage (as a sudo-capable admin):
#   sudo bash agent/deploy/setup_xixi.sh
#   sudo systemctl enable --now homepage-agent
#
set -euo pipefail

AGENT_SRC="$(cd "$(dirname "$0")/.." && pwd)"
XIXI_HOME="${XIXI_HOME:-/var/lib/xixi}"
KNOWLEDGE_DST="${XIXI_HOME}/knowledge"
LOG_DST="${XIXI_HOME}/logs"
RUNTIME_DST="${XIXI_HOME}/runtime"
ENV_DST="${ENV_DST:-/etc/homepage-agent/env}"
UNIT_DST="${UNIT_DST:-/etc/systemd/system/homepage-agent.service}"
RUN_USER="${RUN_USER:-xixi}"
RUN_GROUP="${RUN_GROUP:-xixi}"
PORT="${PORT:-8788}"
BIND="${BIND:-127.0.0.1}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash $0" >&2
  exit 1
fi

echo "[1/6] create system user ${RUN_USER}"
if ! id -u "${RUN_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --home-dir "${XIXI_HOME}" \
    --shell /usr/sbin/nologin --user-group "${RUN_USER}"
else
  echo "  user exists"
  mkdir -p "${XIXI_HOME}"
fi

echo "[2/6] dirs + readonly knowledge sync"
mkdir -p "${KNOWLEDGE_DST}" "${LOG_DST}" "${RUNTIME_DST}" /etc/homepage-agent
# Sync public knowledge only (never .env / logs / venv)
rsync -a --delete \
  --exclude '.git' \
  "${AGENT_SRC}/knowledge/" "${KNOWLEDGE_DST}/"
# knowledge: root-owned, group xixi read-only
chown -R root:"${RUN_GROUP}" "${KNOWLEDGE_DST}"
find "${KNOWLEDGE_DST}" -type d -exec chmod 0550 {} \;
find "${KNOWLEDGE_DST}" -type f -exec chmod 0440 {} \;
chown "${RUN_USER}:${RUN_GROUP}" "${LOG_DST}" "${RUNTIME_DST}"
chmod 0750 "${LOG_DST}" "${RUNTIME_DST}"
# home itself
chown root:"${RUN_GROUP}" "${XIXI_HOME}"
chmod 0750 "${XIXI_HOME}"

echo "[3/6] secrets env at ${ENV_DST} (not under knowledge)"
if [[ ! -f "${ENV_DST}" ]]; then
  # Seed from developer .env if present (keys only live here for service)
  if [[ -f "${AGENT_SRC}/.env" ]]; then
    # shellcheck disable=SC1090
    set -a
    # shellcheck disable=SC1091
    source "${AGENT_SRC}/.env"
    set +a
  fi
  umask 077
  cat > "${ENV_DST}" <<EOF
# Managed by setup_xixi.sh — mode 0640 root:xixi
# Never place this file under knowledge/ or git.
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-https://api.deepseek.com/anthropic}
AGENT_OPENAI_BASE=${AGENT_OPENAI_BASE:-https://api.deepseek.com}
AGENT_MODEL=${AGENT_MODEL:-deepseek-v4-flash}
AGENT_EFFORT=${AGENT_EFFORT:-low}
AGENT_HARNESS=${AGENT_HARNESS:-claude-code}
AGENT_THINKING=disabled
AGENT_CLAUDE_TIMEOUT=${AGENT_CLAUDE_TIMEOUT:-90}
AGENT_CLAUDE_MAX_RETRIES=${AGENT_CLAUDE_MAX_RETRIES:-3}
AGENT_RAG_BUDGET=${AGENT_RAG_BUDGET:-3500}
AGENT_STREAM_PROCESS=1
# Isolation: no model-side local tools; no add-dir
AGENT_CC_TOOLS=
AGENT_CC_ADD_DIR=0
AGENT_CC_ADD_DIRS=
AGENT_SURVEY_PREFETCH=1
AGENT_URL_PREFETCH=1
AGENT_LOG_FULL=0
AGENT_KNOWLEDGE_DIR=${KNOWLEDGE_DST}
AGENT_LOG_DIR=${LOG_DST}
PORT=${PORT}
AGENT_ALLOWED_ORIGINS=${AGENT_ALLOWED_ORIGINS:-https://darkness-hy.github.io,https://hongyuding.site,https://www.hongyuding.site,http://127.0.0.1:4173,http://localhost:4173}
# Optional better general web (leave empty if unused):
# BRAVE_API_KEY=
# SERPER_API_KEY=
# SEARXNG_URL=
# HTTP_PROXY=http://127.0.0.1:7892
# HTTPS_PROXY=http://127.0.0.1:7892
# NO_PROXY=localhost,127.0.0.1
EOF
else
  echo "  ${ENV_DST} exists — leaving in place"
fi
chown root:"${RUN_GROUP}" "${ENV_DST}"
chmod 0640 "${ENV_DST}"

echo "[4/6] ensure agent code tree is group-readable (no .env for xixi)"
# xixi needs to execute code + venv; must NOT read developer .env
chgrp -R "${RUN_GROUP}" "${AGENT_SRC}" || true
# directories traverse
find "${AGENT_SRC}" -type d -exec chmod g+rx {} \;
# code readable
find "${AGENT_SRC}" -type f \( -name '*.py' -o -name '*.sh' -o -name '*.txt' -o -name '*.md' -o -name '*.json' \) \
  -exec chmod g+r {} \; 2>/dev/null || true
# venv binaries
if [[ -d "${AGENT_SRC}/.venv" ]]; then
  chmod -R g+rX "${AGENT_SRC}/.venv" || true
fi
# Lock developer secrets: owner-only
if [[ -f "${AGENT_SRC}/.env" ]]; then
  chown root:root "${AGENT_SRC}/.env" 2>/dev/null || chown "$(stat -c '%U' "${AGENT_SRC}")":"$(stat -c '%G' "${AGENT_SRC}")" "${AGENT_SRC}/.env"
  # Prefer: owner dhy or current tree owner, mode 0600 — never group-readable
  OWNER="$(stat -c '%U' "${AGENT_SRC}")"
  chown "${OWNER}:${OWNER}" "${AGENT_SRC}/.env" || true
  chmod 0600 "${AGENT_SRC}/.env"
fi
# __pycache__ ok
chmod g+rx "${AGENT_SRC}" || true

echo "[5/6] systemd unit ${UNIT_DST}"
CLAUDE_BIN="$(command -v claude || true)"
if [[ -z "${CLAUDE_BIN}" ]]; then
  CLAUDE_BIN="/usr/local/bin/claude"
fi
cat > "${UNIT_DST}" <<EOF
[Unit]
Description=Homepage AI agent (茜茜 / xixi isolation)
After=network.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${AGENT_SRC}
EnvironmentFile=${ENV_DST}
Environment=HOME=${XIXI_HOME}
Environment=AGENT_CLAUDE_BIN=${CLAUDE_BIN}
Environment=PATH=${AGENT_SRC}/.venv/bin:/usr/local/bin:/usr/bin:/bin
# No ambient developer secrets file
Environment=AGENT_CC_TOOLS=
Environment=AGENT_CC_ADD_DIR=0
Environment=AGENT_LOG_FULL=0
# Hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${LOG_DST} ${RUNTIME_DST} /tmp
ReadOnlyPaths=${KNOWLEDGE_DST} ${AGENT_SRC}
# Prevent reading other homes if possible
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes
LockPersonality=yes
# Bind localhost only
ExecStart=${AGENT_SRC}/.venv/bin/python -m uvicorn server:app --host ${BIND} --port ${PORT}
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo "[6/6] verify isolation"
echo "  knowledge: $(ls -ld "${KNOWLEDGE_DST}")"
echo "  env:       $(ls -l "${ENV_DST}")"
echo "  unit:      ${UNIT_DST}"
if sudo -u "${RUN_USER}" test -r "${ENV_DST}"; then
  echo "  xixi can read EnvironmentFile (expected)"
else
  echo "  WARN: xixi cannot read ${ENV_DST}" >&2
fi
if sudo -u "${RUN_USER}" test -r "${AGENT_SRC}/.env" 2>/dev/null; then
  echo "  FAIL: xixi can read agent/.env — fix chmod 0600" >&2
  exit 2
else
  echo "  xixi cannot read agent/.env (expected)"
fi
if sudo -u "${RUN_USER}" test -r "${KNOWLEDGE_DST}/taste.md"; then
  echo "  xixi can read knowledge/taste.md (expected)"
else
  echo "  WARN: xixi cannot read knowledge" >&2
fi

echo
echo "Done. Start with:"
echo "  sudo systemctl enable --now homepage-agent"
echo "  sudo systemctl status homepage-agent"
echo "Sync knowledge later:"
echo "  sudo rsync -a --delete ${AGENT_SRC}/knowledge/ ${KNOWLEDGE_DST}/ && sudo chown -R root:${RUN_GROUP} ${KNOWLEDGE_DST} && sudo find ${KNOWLEDGE_DST} -type d -exec chmod 0550 {} \\; && sudo find ${KNOWLEDGE_DST} -type f -exec chmod 0440 {} \\;"
