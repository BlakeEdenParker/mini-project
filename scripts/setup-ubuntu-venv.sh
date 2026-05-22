#!/usr/bin/env bash
set -euo pipefail

APP_USER="web"
APP_GROUP="web"
VENV_DIR="/var/www/.venv"
APP_DIR="/var/www/html/backend"

if ! getent group "${APP_GROUP}" >/dev/null 2>&1; then
  groupadd --system "${APP_GROUP}"
fi

if ! id "${APP_USER}" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash --gid "${APP_GROUP}" "${APP_USER}"
fi

install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0750 "${VENV_DIR}"

runuser -u "${APP_USER}" -- python3.12 -m venv "${VENV_DIR}"
runuser -u "${APP_USER}" -- "${VENV_DIR}/bin/python" -m pip install --upgrade pip wheel
runuser -u "${APP_USER}" -- "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"

chown -R "${APP_USER}:${APP_GROUP}" "${VENV_DIR}"
chmod -R u+rwX,go-rwx "${VENV_DIR}"

echo "venv ready: ${VENV_DIR}"
