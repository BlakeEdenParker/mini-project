# Mini Board

Flask, Gunicorn, nginx, MariaDB 조합으로 운영할 게시판 프로젝트 골격입니다.

## Directory

```text
mini-project/
  service/
    app.py
    requirements.txt
    .env.example
    templates/
      base.html
      auth/
        login.html
      posts/
        list.html
        detail.html
        form.html
      errors/
        403.html
        404.html
    static/
      css/
        main.css
      js/
        main.js
      images/
  nginx/
    app-locations/
      board.conf
    sites-available/
      mini-board.conf
    sites-enabled/
    logs/
  database/
    init.sql
  deploy/
    apps/
      board.env
    db/
      board.env
  systemd/
    board.service
  scripts/
    init-db-server.sh
    init-web-server.sh
    run-dev.ps1
    setup-ubuntu-venv.sh
```

## First Scope

- Public pages: post list, post detail
- Login required pages: post create, edit, delete
- Ownership rule: the post author or admin can edit/delete
- Admin users see `관리자 권한 사용중.` in the page header
- DB server: `10.0.2.11/24`
- Web server: `10.0.2.10/24`
- Future service targets: session login, CSRF protection, MariaDB repository layer, pagination

## Ubuntu Layout

Deploy this project under `/var/www/html`.

```text
/var/www/html/
  service/
  nginx/
  database/
```

## Git-Based Init Scripts

Use separate scripts per server role:

- web Ubuntu `10.0.2.10`: `scripts/init-web-server.sh`
- DB Ubuntu `10.0.2.11`: `scripts/init-db-server.sh`

The reusable web init script is `scripts/init-web-server.sh`. App-specific values live in `deploy/apps/*.env`, so future services can add their own env file, port, nginx config, and systemd unit without rewriting the common setup.

For the current board app on Ubuntu 24.04:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/your-org/your-repo.git /tmp/mini-project
cd /tmp/mini-project
sudo env REPO_URL=https://github.com/your-org/your-repo.git ./scripts/init-web-server.sh
```

If the project folder is already copied locally, `REPO_URL` is optional:

```bash
cd /tmp/mini-project
sudo ./scripts/init-web-server.sh
```

If the repo is already cloned at `/var/www/html`, edit `/var/www/html/deploy/apps/board.env` and set `REPO_URL`, then run:

```bash
cd /var/www/html
sudo bash scripts/init-web-server.sh deploy/apps/board.env
```

The script:

- installs `git`, `nginx`, `python3.12`, `python3.12-venv`, and `python3-pip`
- creates the `web` service user when missing
- clones or updates the repo into `/var/www/html`
- creates `/var/www/.venv`
- installs Python packages as the `web` user
- copies systemd and nginx configs into `/etc`
- disables nginx's default site
- starts the Gunicorn service and reloads nginx

For the DB server:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/your-org/your-repo.git /tmp/mini-project
cd /tmp/mini-project
sudo env REPO_URL=https://github.com/your-org/your-repo.git ./scripts/init-db-server.sh
```

If the project folder is already copied locally, `REPO_URL` is optional:

```bash
cd /tmp/mini-project
sudo ./scripts/init-db-server.sh
```

The DB script:

- installs `git`, `mariadb-server`, and `mariadb-client`
- clones or updates the repo into `/var/www/html`
- writes MariaDB bind config to listen on `10.0.2.11`
- enables and restarts MariaDB
- runs `database/init.sql`
- creates `board_db`
- grants app DB access only to `board_app` from `10.0.2.10`

For additional web apps later, copy `deploy/apps/board.env`, change `APP_NAME`, `APP_ROOT`, `GUNICORN_BIND`, `SYSTEMD_SOURCE`, `NGINX_SOURCE`, and `NGINX_LOCATION_SOURCE`, then add matching systemd/nginx files. nginx keeps one port-80 server block and loads app routes from `/etc/nginx/app-locations/*.conf`, which avoids fighting over the default site.

The default branch in the sample env files is `master`, matching this repository. Change `REPO_BRANCH` if the GitHub repo uses another branch.

Python uses the Ubuntu system `python3.12`, but packages are installed into `/var/www/.venv`.

```bash
sudo bash /var/www/html/scripts/setup-ubuntu-venv.sh
```

The script makes sure:

- the service user is `web`
- the virtual environment path is `/var/www/.venv`
- `/var/www/.venv` is owned by `web:web`
- permissions are `u+rwX,go-rwx`, so the `web` user can run `pip` inside the venv

Manual equivalent:

```bash
sudo useradd --system --create-home --shell /bin/bash web
sudo install -d -o web -g web -m 0750 /var/www/.venv
sudo runuser -u web -- python3.12 -m venv /var/www/.venv
sudo runuser -u web -- /var/www/.venv/bin/python -m pip install --upgrade pip wheel
sudo runuser -u web -- /var/www/.venv/bin/pip install -r /var/www/html/service/requirements.txt
sudo chown -R web:web /var/www/.venv
sudo chmod -R u+rwX,go-rwx /var/www/.venv
```

Gunicorn should listen on the web Ubuntu host only:

```bash
cd /var/www/html/service
/var/www/.venv/bin/gunicorn -w 3 -b 127.0.0.1:8000 app:app
```

systemd example:

```bash
sudo cp /var/www/html/systemd/board.service /etc/systemd/system/board.service
sudo systemctl daemon-reload
sudo systemctl enable --now board
sudo systemctl status board
```

nginx receives port 80 traffic and reverse-proxies page routes to Gunicorn. Static files are served from `/var/www/html/service/static`.

Run `database/init.sql` on the DB Ubuntu host. It creates `board_db`, seeds the sample posts, and grants app DB access only to `board_app` from `10.0.2.10`.

Admin seed account:

- ID: `admin`
- Password: `admin1234`

Change this password before real use.

## Local Flask Run

```powershell
cd service
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.
