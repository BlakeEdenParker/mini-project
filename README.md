# Mini Board

Flask, Gunicorn, nginx, MariaDB 조합으로 운영하는 게시판 프로토타입입니다.

## 폴더 구조

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

## 현재 구현 범위

- 비로그인 사용자도 게시글 목록과 상세 페이지를 볼 수 있습니다.
- 글 작성, 수정, 삭제는 로그인 후 사용할 수 있습니다.
- 게시글 작성자 또는 관리자만 수정/삭제할 수 있습니다.
- 관리자로 로그인하면 헤더에 `관리자 권한 사용중.` 문구가 표시됩니다.
- Web 서버 기준 IP: `10.0.2.10/24`
- DB 서버 기준 IP: `10.0.2.11/24`
- 이후 추가 예정: 세션 로그인 고도화, CSRF 보호, MariaDB 연동 코드, 페이지네이션

## Ubuntu 배포 기준

프로젝트는 Ubuntu 24.04에서 `/var/www/html` 아래에 배치하는 기준으로 작성되어 있습니다.

```text
/var/www/html/
  service/
  nginx/
  database/
```

Python은 Ubuntu의 기본 `python3.12`를 사용하고, 가상환경은 `/var/www/.venv`에 생성합니다.

## 초기화 스크립트

서버 역할에 따라 초기화 스크립트가 분리되어 있습니다.

- Web 서버 `10.0.2.10`: `scripts/init-web-server.sh`
- DB 서버 `10.0.2.11`: `scripts/init-db-server.sh`

공통 설정값은 `deploy/apps/board.env`, DB 설정값은 `deploy/db/board.env`에 있습니다.

## Web 서버 초기화

GitHub에서 받아 실행하는 경우:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/BlakeEdenParker/mini-project.git /tmp/mini-project
cd /tmp/mini-project
sudo env REPO_URL=https://github.com/BlakeEdenParker/mini-project.git ./scripts/init-web-server.sh
```

프로젝트 폴더를 이미 로컬에 복사해둔 경우에는 `REPO_URL` 없이 실행할 수 있습니다.

```bash
cd /tmp/mini-project
sudo ./scripts/init-web-server.sh
```

Web 초기화 스크립트는 다음 작업을 수행합니다.

- `git`, `nginx`, `python3.12`, `python3.12-venv`, `python3-pip` 설치
- `web` 서비스 사용자 생성
- 프로젝트를 `/var/www/html`로 복사하거나 Git 저장소에서 갱신
- `/var/www/.venv` 가상환경 생성
- `web` 사용자 권한으로 Python 패키지 설치
- systemd 서비스 파일 설치
- nginx 설정 설치
- nginx 기본 사이트 비활성화
- Gunicorn 서비스 시작
- nginx 설정 검사 후 reload

## DB 서버 초기화

GitHub에서 받아 실행하는 경우:

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/BlakeEdenParker/mini-project.git /tmp/mini-project
cd /tmp/mini-project
sudo env REPO_URL=https://github.com/BlakeEdenParker/mini-project.git ./scripts/init-db-server.sh
```

프로젝트 폴더를 이미 로컬에 복사해둔 경우에는 `REPO_URL` 없이 실행할 수 있습니다.

```bash
cd /tmp/mini-project
sudo ./scripts/init-db-server.sh
```

DB 초기화 스크립트는 다음 작업을 수행합니다.

- `git`, `mariadb-server`, `mariadb-client` 설치
- 프로젝트를 `/var/www/html`로 복사하거나 Git 저장소에서 갱신
- MariaDB가 `10.0.2.11`에서 listen 하도록 설정
- MariaDB 활성화 및 재시작
- `database/init.sql` 실행
- `board_db` 데이터베이스 생성
- `board_app` 계정에 `10.0.2.10`에서만 접속 권한 부여

DB 서버에서 `10.0.2.11` IP가 아직 설정되어 있지 않으면 스크립트가 중단됩니다. 먼저 DB Ubuntu 서버의 내부 IP를 설정해야 합니다.

## 가상환경 수동 설정

가상환경만 별도로 만들고 싶다면 다음 스크립트를 사용할 수 있습니다.

```bash
sudo /var/www/html/scripts/setup-ubuntu-venv.sh
```

수동으로 수행하면 다음과 같습니다.

```bash
sudo useradd --system --create-home --shell /bin/bash web
sudo install -d -o web -g web -m 0750 /var/www/.venv
sudo runuser -u web -- python3.12 -m venv /var/www/.venv
sudo runuser -u web -- /var/www/.venv/bin/python -m pip install --upgrade pip wheel
sudo runuser -u web -- /var/www/.venv/bin/pip install -r /var/www/html/service/requirements.txt
sudo chown -R web:web /var/www/.venv
sudo chmod -R u+rwX,go-rwx /var/www/.venv
```

## Gunicorn 실행 기준

Gunicorn은 Web 서버 내부에서만 접근되도록 `127.0.0.1:8000`에 바인딩합니다.

```bash
cd /var/www/html/service
/var/www/.venv/bin/gunicorn -w 3 -b 127.0.0.1:8000 app:app
```

systemd로 실행하는 경우:

```bash
sudo cp /var/www/html/systemd/board.service /etc/systemd/system/board.service
sudo systemctl daemon-reload
sudo systemctl enable --now board
sudo systemctl status board
```

nginx는 80 포트로 들어온 요청을 Gunicorn으로 reverse proxy 합니다. 정적 파일은 `/var/www/html/service/static`에서 제공합니다.

## DB 초기 데이터

`database/init.sql`은 다음 내용을 생성합니다.

- `board_db` 데이터베이스
- `users` 테이블
- `posts` 테이블
- 관리자 계정
- 예시 게시글 3개

관리자 초기 계정:

```text
ID: admin
Password: admin1234
```

운영 환경에서는 반드시 관리자 비밀번호와 DB 비밀번호를 변경해야 합니다.

## 로컬 개발 실행

Windows PowerShell 기준:

```powershell
cd service
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python app.py
```

브라우저에서 다음 주소로 접속합니다.

```text
http://127.0.0.1:5000
```

## 확인 명령

Web 서버에서 서비스 상태를 확인하려면 다음 명령을 사용합니다.

```bash
systemctl status board
systemctl status nginx
curl http://127.0.0.1/posts
```

브라우저에서는 다음 주소로 접속합니다.

```text
http://WEB서버IP/posts
```
