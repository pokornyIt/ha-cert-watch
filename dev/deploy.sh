#!/usr/bin/env bash
set -euo pipefail

# ---- Config (override via env) ----------------------------------------------
HA_HOST="${HA_HOST:-192.168.7.141}"
HA_USER="${HA_USER:-root}"
HA_PORT="${HA_PORT:-22}"

# Home Assistant config directory on the target
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/config}"

DOMAIN="${DOMAIN:-cert_watch}"
SRC_DIR="${SRC_DIR:-custom_components/${DOMAIN}}"
DST_DIR="${HA_CONFIG_DIR}/custom_components/${DOMAIN}"

# rsync is preferred; fallback to scp
USE_RSYNC="${USE_RSYNC:-1}"

# Restart options:
#   - "ha"  -> run: ha core restart
#   - "cmd" -> run custom command via RESTART_CMD
#   - "no"  -> don't restart
RESTART_MODE="${RESTART_MODE:-ha}"
RESTART_CMD="${RESTART_CMD:-}"

# -----------------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSH_OPTS=(-p "${HA_PORT}" -o StrictHostKeyChecking=accept-new)

echo "Deploying ${DOMAIN} to ${HA_USER}@${HA_HOST}:${DST_DIR}"
echo "Source: ${REPO_ROOT}/${SRC_DIR}"

# Ensure target dir exists
ssh "${SSH_OPTS[@]}" "${HA_USER}@${HA_HOST}" "mkdir -p '${DST_DIR}'"

if [[ "${USE_RSYNC}" == "1" ]] && command -v rsync >/dev/null 2>&1; then
  rsync -az --delete \
    -e "ssh ${SSH_OPTS[*]}" \
    "${REPO_ROOT}/${SRC_DIR}/" \
    "${HA_USER}@${HA_HOST}:${DST_DIR}/"
else
  echo "rsync not available (or disabled); using scp (no delete sync)"
  scp "${SSH_OPTS[@]}" -r "${REPO_ROOT}/${SRC_DIR}/." "${HA_USER}@${HA_HOST}:${DST_DIR}/"
fi

echo "Deploy done."

case "${RESTART_MODE}" in
  ha)
    echo "Restarting Home Assistant Core (ha core restart)..."
    ssh "${SSH_OPTS[@]}" "${HA_USER}@${HA_HOST}" "ha core restart"
    ;;
  cmd)
    if [[ -z "${RESTART_CMD}" ]]; then
      echo "RESTART_MODE=cmd but RESTART_CMD is empty" >&2
      exit 1
    fi
    echo "Restarting using custom command: ${RESTART_CMD}"
    ssh "${SSH_OPTS[@]}" "${HA_USER}@${HA_HOST}" "${RESTART_CMD}"
    ;;
  no)
    echo "Restart skipped (RESTART_MODE=no)."
    ;;
  *)
    echo "Unknown RESTART_MODE: ${RESTART_MODE} (use ha|cmd|no)" >&2
    exit 1
    ;;
esac

echo "OK"
