CREATE DATABASE IF NOT EXISTS `zhixun`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `zhixun`;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    openid VARCHAR(64) NOT NULL,
    nickname VARCHAR(100) NOT NULL DEFAULT '学习者',
    avatar_url VARCHAR(500) NOT NULL DEFAULT '',
    total_xp INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_openid (openid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS quiz_sessions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    quiz_id VARCHAR(64) NOT NULL,
    user_id BIGINT UNSIGNED NULL,
    title VARCHAR(255) NOT NULL,
    summary TEXT NULL,
    user_input TEXT NULL,
    questions_json JSON NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_quiz_sessions_quiz_id (quiz_id),
    KEY idx_quiz_sessions_user_id (user_id),
    KEY idx_quiz_sessions_created_at (created_at),
    CONSTRAINT fk_quiz_sessions_user_id
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS answer_records (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    quiz_id VARCHAR(64) NOT NULL,
    user_id BIGINT UNSIGNED NULL,
    records_json JSON NOT NULL,
    total_questions INT NOT NULL,
    correct_count INT NOT NULL,
    accuracy DECIMAL(5, 2) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_answer_records_quiz_id (quiz_id),
    KEY idx_answer_records_user_id (user_id),
    KEY idx_answer_records_created_at (created_at),
    CONSTRAINT fk_answer_records_user_id
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_answer_records_quiz_id
        FOREIGN KEY (quiz_id) REFERENCES quiz_sessions (quiz_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS reports (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    quiz_id VARCHAR(64) NOT NULL,
    user_id BIGINT UNSIGNED NULL,
    report_json JSON NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_reports_quiz_id (quiz_id),
    KEY idx_reports_user_id (user_id),
    KEY idx_reports_created_at (created_at),
    CONSTRAINT fk_reports_user_id
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_reports_quiz_id
        FOREIGN KEY (quiz_id) REFERENCES quiz_sessions (quiz_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS admin_users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
    login_name VARCHAR(64) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL DEFAULT '管理员',
    role VARCHAR(20) NOT NULL DEFAULT 'tenant_admin',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_admin_users_tenant_login (tenant_code, login_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS question_banks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
    name VARCHAR(200) NOT NULL,
    description TEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_question_banks_tenant_name (tenant_code, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS questions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
    bank_id BIGINT UNSIGNED NOT NULL,
    type VARCHAR(20) NOT NULL,
    stem TEXT NOT NULL,
    options_json JSON NOT NULL,
    answer_json JSON NOT NULL,
    explanation TEXT NOT NULL,
    knowledge_point VARCHAR(255) NOT NULL DEFAULT '',
    difficulty VARCHAR(20) NOT NULL DEFAULT 'medium',
    source_ref VARCHAR(255) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    ai_meta VARCHAR(255) NOT NULL DEFAULT '',
    review_note VARCHAR(500) NULL,
    reviewed_by VARCHAR(64) NULL,
    reviewed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_questions_tenant_status (tenant_code, status),
    KEY idx_questions_tenant_bank (tenant_code, bank_id),
    CONSTRAINT fk_questions_bank
        FOREIGN KEY (bank_id) REFERENCES question_banks (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS knowledge_cards (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
    doc_name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    excerpt TEXT NOT NULL,
    content_json JSON NULL,
    source_ref VARCHAR(255) NOT NULL DEFAULT '',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    view_rate INT NOT NULL DEFAULT 0,
    created_by VARCHAR(64) NULL,
    published_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_knowledge_cards_tenant_status (tenant_code, status),
    KEY idx_knowledge_cards_tenant_created (tenant_code, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
