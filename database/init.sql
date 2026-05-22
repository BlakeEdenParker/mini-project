CREATE DATABASE IF NOT EXISTS board_db
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'board_app'@'10.0.2.10' IDENTIFIED BY 'change-this-db-password';
GRANT SELECT, INSERT, UPDATE, DELETE ON board_db.* TO 'board_app'@'10.0.2.10';
FLUSH PRIVILEGES;

USE board_db;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(80) NOT NULL,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS posts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  author_id BIGINT UNSIGNED NOT NULL,
  title VARCHAR(120) NOT NULL,
  content TEXT NOT NULL,
  view_count INT UNSIGNED NOT NULL DEFAULT 0,
  is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_posts_author_id (author_id),
  KEY idx_posts_created_at (created_at),
  CONSTRAINT fk_posts_author_id FOREIGN KEY (author_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO users (id, username, password_hash, display_name, is_admin)
VALUES
  (1, 'admin', 'scrypt:32768:8:1$6iGWMyFb7HZDipUh$48621b4676950c8ff87c26cfa1c5416baf8fe3a669e6788a3499749199dbc9c68275c70b8744bcbe8e78bc52770eb5cd28fe492fe37942bea3f1051f0c548a15', 'admin', TRUE),
  (2, 'demo', 'scrypt:32768:8:1$6iGWMyFb7HZDipUh$48621b4676950c8ff87c26cfa1c5416baf8fe3a669e6788a3499749199dbc9c68275c70b8744bcbe8e78bc52770eb5cd28fe492fe37942bea3f1051f0c548a15', 'demo', FALSE)
ON DUPLICATE KEY UPDATE
  password_hash = VALUES(password_hash),
  display_name = VALUES(display_name),
  is_admin = VALUES(is_admin);

INSERT INTO posts (id, author_id, title, content, view_count, created_at)
VALUES
  (1, 1, '공개로 볼 수 있는 페이지', '목록과 상세 페이지는 로그인하지 않아도 접근할 수 있습니다.', 31, '2026-05-20 00:00:00'),
  (2, 2, '로그인이 필요한 동작', '작성, 수정, 삭제는 로그인 여부와 작성자 권한을 서버에서 확인해야 합니다.', 7, '2026-05-21 00:00:00'),
  (3, 1, '게시판 화면 구조 초안', '목록, 상세, 작성, 수정 화면을 먼저 맞춘 뒤 인증과 DB를 연결합니다.', 12, '2026-05-22 00:00:00')
ON DUPLICATE KEY UPDATE
  author_id = VALUES(author_id),
  title = VALUES(title),
  content = VALUES(content),
  view_count = VALUES(view_count),
  created_at = VALUES(created_at);
