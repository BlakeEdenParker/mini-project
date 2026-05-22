#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-deploy/apps/board.env}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash scripts/init-web-server.sh" >&2
  exit 1
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Missing config: ${CONFIG_PATH}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${CONFIG_PATH}"

REPO_URL="${REPO_URL:-${2:-}}"

if [[ -z "${REPO_URL}" && ! -d "${APP_ROOT}/.git" ]]; then
  echo "Set REPO_URL in ${CONFIG_PATH}, or run: sudo REPO_URL=https://... bash scripts/init-web-server.sh" >&2
  exit 1
fi

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

if [[ -d "${APP_ROOT}/.git" ]]; then
  git -C "${APP_ROOT}" fetch --all --prune
  git -C "${APP_ROOT}" checkout "${REPO_BRANCH}"
  git -C "${APP_ROOT}" pull --ff-only origin "${REPO_BRANCH}"
else
  rm -rf "${APP_ROOT}"
  git clone --branch "${REPO_BRANCH}" "${REPO_URL}" "${APP_ROOT}"
fi

chown -R "${APP_USER}:${APP_GROUP}" "${APP_ROOT}"

install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0750 "${VENV_DIR}"
runuser -u "${APP_USER}" -- "${PYTHON_BIN}" -m venv "${VENV_DIR}"
runuser -u "${APP_USER}" -- "${VENV_DIR}/bin/python" -m pip install --upgrade pip wheel
runuser -u "${APP_USER}" -- "${VENV_DIR}/bin/pip" install -r "${APP_ROOT}/${REQUIREMENTS_FILE}"
chown -R "${APP_USER}:${APP_GROUP}" "${VENV_DIR}"
chmod -R u+rwX,go-rwx "${VENV_DIR}"

install -m 0644 "${APP_ROOT}/${SYSTEMD_SOURCE}" "${SYSTEMD_TARGET}"
install -d -m 0755 "$(dirname "${NGINX_LOCATION_TARGET}")"
install -m 0644 "${APP_ROOT}/${NGINX_LOCATION_SOURCE}" "${NGINX_LOCATION_TARGET}"
install -m 0644 "${APP_ROOT}/${NGINX_SOURCE}" "${NGINX_AVAILABLE}"
ln -sfn "${NGINX_AVAILABLE}" "${NGINX_ENABLED}"
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable --now "$(basename "${SYSTEMD_TARGET}")"
nginx -t
systemctl reload nginx

echo "${APP_NAME} initialized from git at ${APP_ROOT}"
