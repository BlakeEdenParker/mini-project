#!/usr/bin/env bash
set -Eeuo pipefail

CONFIG_PATH="${1:-deploy/apps/board.env}"
INPUT_REPO_URL="${REPO_URL:-}"
INPUT_REPO_BRANCH="${REPO_BRANCH:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

log() {
  printf '[web-init] %s\n' "$*"
}

fail() {
  printf '[web-init] ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${EUID}" -ne 0 ]]; then
  fail "Run as root: sudo ./scripts/init-web-server.sh"
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
  nginx \
  "${PYTHON_BIN}" \
  "${PYTHON_BIN}-venv" \
  python3-pip

if ! getent group "${APP_GROUP}" >/dev/null 2>&1; then
  groupadd --system "${APP_GROUP}"
fi

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash --gid "${APP_GROUP}" "${APP_USER}"
fi

install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "$(dirname "${APP_ROOT}")"

if [[ -n "${REPO_URL}" ]]; then
  if [[ -d "${APP_ROOT}/.git" ]]; then
    log "Updating existing git checkout at ${APP_ROOT}"
    git -C "${APP_ROOT}" fetch --all --prune
    git -C "${APP_ROOT}" checkout "${REPO_BRANCH}"
    git -C "${APP_ROOT}" pull --ff-only origin "${REPO_BRANCH}"
  else
    log "Cloning ${REPO_URL} into ${APP_ROOT}"
    rm -rf "${APP_ROOT}"
    git clone --branch "${REPO_BRANCH}" "${REPO_URL}" "${APP_ROOT}"
  fi
elif [[ "${SOURCE_ROOT}" != "${APP_ROOT}" ]]; then
  log "No REPO_URL set; copying local source ${SOURCE_ROOT} into ${APP_ROOT}"
  rm -rf "${APP_ROOT}"
  install -d -m 0755 "${APP_ROOT}"
  cp -a "${SOURCE_ROOT}/." "${APP_ROOT}/"
elif [[ -d "${APP_ROOT}/.git" ]]; then
  log "No REPO_URL set; using existing local checkout at ${APP_ROOT}"
else
  fail "No local source or git checkout found for ${APP_ROOT}"
fi

chown -R "${APP_USER}:${APP_GROUP}" "${APP_ROOT}"

log "Creating Python virtual environment at ${VENV_DIR}"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0750 "${VENV_DIR}"
runuser -u "${APP_USER}" -- "${PYTHON_BIN}" -m venv "${VENV_DIR}"
runuser -u "${APP_USER}" -- "${VENV_DIR}/bin/python" -m pip install --upgrade pip wheel
runuser -u "${APP_USER}" -- "${VENV_DIR}/bin/pip" install -r "${APP_ROOT}/${REQUIREMENTS_FILE}"
chown -R "${APP_USER}:${APP_GROUP}" "${VENV_DIR}"
chmod -R u+rwX,go-rwx "${VENV_DIR}"

log "Installing systemd and nginx configuration"
install -m 0644 "${APP_ROOT}/${SYSTEMD_SOURCE}" "${SYSTEMD_TARGET}"
install -d -m 0755 "$(dirname "${NGINX_LOCATION_TARGET}")"
install -m 0644 "${APP_ROOT}/${NGINX_LOCATION_SOURCE}" "${NGINX_LOCATION_TARGET}"
install -m 0644 "${APP_ROOT}/${NGINX_SOURCE}" "${NGINX_AVAILABLE}"
ln -sfn "${NGINX_AVAILABLE}" "${NGINX_ENABLED}"
rm -f /etc/nginx/sites-enabled/default

log "Starting service and reloading nginx"
systemctl daemon-reload
systemctl enable --now "$(basename "${SYSTEMD_TARGET}")"
nginx -t
systemctl reload nginx

log "${APP_NAME} initialized at ${APP_ROOT}"
