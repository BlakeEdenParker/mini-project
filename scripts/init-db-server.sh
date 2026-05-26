#!/usr/bin/env bash
set -Eeuo pipefail

CONFIG_PATH="${1:-deploy/db/board.env}"
INPUT_REPO_URL="${REPO_URL:-}"
INPUT_REPO_BRANCH="${REPO_BRANCH:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

log() {
  printf '[db-init] %s\n' "$*"
}

fail() {
  printf '[db-init] ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${EUID}" -ne 0 ]]; then
  fail "Run as root: sudo ./scripts/init-db-server.sh"
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  if [[ -f "${SOURCE_ROOT}/${CONFIG_PATH}" ]]; then
    CONFIG_PATH="${SOURCE_ROOT}/${CONFIG_PATH}"
  else
    fail "Missing config: ${CONFIG_PATH}"
  fi
fi

# shellcheck disable=SC1090
source "${CONFIG_PATH}"

REPO_URL="${INPUT_REPO_URL:-${REPO_URL:-${2:-}}}"
REPO_BRANCH="${INPUT_REPO_BRANCH:-${REPO_BRANCH}}"

log "Installing Ubuntu 24.04 packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git \
  mariadb-server \
  mariadb-client

if [[ -n "${REPO_URL}" ]]; then
  if [[ -d "${REPO_ROOT}/.git" ]]; then
    log "Updating existing git checkout at ${REPO_ROOT}"
    git -C "${REPO_ROOT}" fetch --all --prune
    git -C "${REPO_ROOT}" checkout "${REPO_BRANCH}"
    git -C "${REPO_ROOT}" pull --ff-only origin "${REPO_BRANCH}"
  else
    log "Cloning ${REPO_URL} into ${REPO_ROOT}"
    rm -rf "${REPO_ROOT}"
    git clone --branch "${REPO_BRANCH}" "${REPO_URL}" "${REPO_ROOT}"
  fi
elif [[ "${SOURCE_ROOT}" != "${REPO_ROOT}" ]]; then
  log "No REPO_URL set; copying local source ${SOURCE_ROOT} into ${REPO_ROOT}"
  rm -rf "${REPO_ROOT}"
  install -d -m 0755 "${REPO_ROOT}"
  cp -a "${SOURCE_ROOT}/." "${REPO_ROOT}/"
elif [[ -d "${REPO_ROOT}/.git" ]]; then
  log "No REPO_URL set; using existing local checkout at ${REPO_ROOT}"
else
  fail "No local source or git checkout found for ${REPO_ROOT}"
fi

if ! ip -4 addr show | grep -q "inet ${MARIADB_BIND_ADDRESS}/"; then
  fail "IP ${MARIADB_BIND_ADDRESS} is not configured on this server. Set DB Ubuntu IP before starting MariaDB."
fi

log "Writing MariaDB bind config"
cat > "${MARIADB_CONFIG_FILE}" <<EOF
[mysqld]
bind-address = ${MARIADB_BIND_ADDRESS}
skip-name-resolve
EOF

log "Starting MariaDB"
systemctl enable --now mariadb
systemctl restart mariadb

log "Applying SQL seed ${INIT_SQL_SOURCE}"
mysql < "${REPO_ROOT}/${INIT_SQL_SOURCE}"

log "MariaDB initialized on ${DB_SERVER_IP}; app access allowed from ${WEB_SERVER_IP}"
