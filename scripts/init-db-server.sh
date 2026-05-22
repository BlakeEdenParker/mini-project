#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-deploy/db/board.env}"
INPUT_REPO_URL="${REPO_URL:-}"
INPUT_REPO_BRANCH="${REPO_BRANCH:-}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash scripts/init-db-server.sh" >&2
  exit 1
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Missing config: ${CONFIG_PATH}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${CONFIG_PATH}"

REPO_URL="${INPUT_REPO_URL:-${REPO_URL:-${2:-}}}"
REPO_BRANCH="${INPUT_REPO_BRANCH:-${REPO_BRANCH}}"

if [[ -z "${REPO_URL}" && ! -d "${REPO_ROOT}/.git" ]]; then
  echo "Set REPO_URL in ${CONFIG_PATH}, or run: sudo REPO_URL=https://... bash scripts/init-db-server.sh" >&2
  exit 1
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git \
  mariadb-server \
  mariadb-client

if [[ -d "${REPO_ROOT}/.git" ]]; then
  git -C "${REPO_ROOT}" fetch --all --prune
  git -C "${REPO_ROOT}" checkout "${REPO_BRANCH}"
  git -C "${REPO_ROOT}" pull --ff-only origin "${REPO_BRANCH}"
else
  rm -rf "${REPO_ROOT}"
  git clone --branch "${REPO_BRANCH}" "${REPO_URL}" "${REPO_ROOT}"
fi

cat > "${MARIADB_CONFIG_FILE}" <<EOF
[mysqld]
bind-address = ${MARIADB_BIND_ADDRESS}
skip-name-resolve
EOF

systemctl enable --now mariadb
systemctl restart mariadb

mysql < "${REPO_ROOT}/${INIT_SQL_SOURCE}"

echo "MariaDB initialized on ${DB_SERVER_IP}; app access allowed from ${WEB_SERVER_IP}"
