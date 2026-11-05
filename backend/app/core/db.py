"""MySQL 连接与初始化。"""

from __future__ import annotations

from typing import Final

import aiomysql
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

_pool: aiomysql.Pool | None = None

SCHEMA_STATEMENTS: Final[list[str]] = [
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS quiz_tasks (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        task_id VARCHAR(64) NOT NULL,
        user_id BIGINT UNSIGNED NULL,
        status ENUM('pending', 'running', 'completed', 'failed') NOT NULL DEFAULT 'pending',
        user_input TEXT NOT NULL,
        question_count INT NOT NULL DEFAULT 5,
        difficulty VARCHAR(10) NOT NULL DEFAULT 'mixed',
        result_json JSON NULL,
        error_message VARCHAR(500) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_quiz_tasks_task_id (task_id),
        KEY idx_quiz_tasks_user_id (user_id),
        KEY idx_quiz_tasks_status (status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS kb_documents (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        doc_id VARCHAR(64) NOT NULL,
        user_id BIGINT UNSIGNED NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        file_type VARCHAR(20) NOT NULL,
        file_size INT NOT NULL,
        status ENUM('processing', 'ready', 'failed') NOT NULL DEFAULT 'processing',
        chunk_count INT NOT NULL DEFAULT 0,
        error_message VARCHAR(500) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_kb_documents_doc_id (doc_id),
        KEY idx_kb_documents_user_id (user_id),
        CONSTRAINT fk_kb_documents_user_id
            FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS image_generation_logs (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        user_id BIGINT UNSIGNED NOT NULL,
        quiz_id VARCHAR(64) NULL,
        question_id VARCHAR(32) NULL,
        image_url VARCHAR(500) NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_image_gen_logs_user_created (user_id, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
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
        deleted_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_questions_tenant_status (tenant_code, status),
        KEY idx_questions_tenant_bank (tenant_code, bank_id),
        CONSTRAINT fk_questions_bank
            FOREIGN KEY (bank_id) REFERENCES question_banks (id)
            ON DELETE RESTRICT ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_cards (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        doc_id BIGINT UNSIGNED NULL,
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS org_units (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        parent_id BIGINT UNSIGNED NULL,
        name VARCHAR(200) NOT NULL,
        path VARCHAR(500) NOT NULL DEFAULT '',
        sort INT NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_org_units_tenant_parent_name (tenant_code, parent_id, name),
        KEY idx_org_units_tenant_parent_sort (tenant_code, parent_id, sort),
        CONSTRAINT fk_org_units_parent
            FOREIGN KEY (parent_id) REFERENCES org_units (id)
            ON DELETE RESTRICT ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS employees (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        org_id BIGINT UNSIGNED NULL,
        user_id BIGINT UNSIGNED NULL,
        employee_no VARCHAR(64) NOT NULL,
        name VARCHAR(100) NOT NULL,
        role VARCHAR(30) NOT NULL DEFAULT '员工',
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        notify_deadline TINYINT(1) NOT NULL DEFAULT 1,
        invite_code VARCHAR(32) NOT NULL,
        invite_status VARCHAR(20) NOT NULL DEFAULT 'unbound',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_employees_tenant_no (tenant_code, employee_no),
        UNIQUE KEY uk_employees_tenant_invite (tenant_code, invite_code),
        UNIQUE KEY uk_employees_user (user_id),
        KEY idx_employees_tenant_org_status (tenant_code, org_id, status),
        CONSTRAINT fk_employees_org
            FOREIGN KEY (org_id) REFERENCES org_units (id)
            ON DELETE SET NULL ON UPDATE CASCADE,
        CONSTRAINT fk_employees_user
            FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE SET NULL ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS employee_join_requests (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        user_id BIGINT UNSIGNED NOT NULL,
        name VARCHAR(100) NOT NULL,
        employee_no VARCHAR(64) NOT NULL,
        org_id BIGINT UNSIGNED NULL,
        role VARCHAR(30) NOT NULL DEFAULT '员工',
        remark VARCHAR(500) NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        reject_reason VARCHAR(500) NULL,
        reviewed_by VARCHAR(64) NULL,
        reviewed_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_join_requests_tenant_status (tenant_code, status, created_at),
        KEY idx_join_requests_user_status (user_id, status),
        CONSTRAINT fk_join_requests_user
            FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_join_requests_org
            FOREIGN KEY (org_id) REFERENCES org_units (id)
            ON DELETE SET NULL ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS admin_documents (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        file_name VARCHAR(255) NOT NULL,
        file_type VARCHAR(20) NOT NULL,
        file_size INT NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'processing',
        chunks INT NOT NULL DEFAULT 0,
        error_message VARCHAR(500) NULL,
        file_path VARCHAR(500) NULL,
        created_by VARCHAR(64) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_admin_documents_tenant_status (tenant_code, status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS exams (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        title VARCHAR(255) NOT NULL,
        description TEXT NULL,
        bank_id BIGINT UNSIGNED NOT NULL,
        question_count INT NOT NULL DEFAULT 5,
        pass_score INT NOT NULL DEFAULT 60,
        duration_minutes INT NOT NULL DEFAULT 30,
        max_attempts INT NOT NULL DEFAULT 1,
        start_at DATETIME NULL,
        end_at DATETIME NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'draft',
        created_by VARCHAR(64) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_exams_tenant_status (tenant_code, status),
        CONSTRAINT fk_exams_bank
            FOREIGN KEY (bank_id) REFERENCES question_banks (id)
            ON DELETE RESTRICT ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS exam_questions (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        exam_id BIGINT UNSIGNED NOT NULL,
        question_id BIGINT UNSIGNED NULL,
        snapshot_json JSON NOT NULL,
        sort INT NOT NULL DEFAULT 0,
        score DECIMAL(5,2) NOT NULL DEFAULT 0,
        PRIMARY KEY (id),
        UNIQUE KEY uk_exam_questions_exam_question (exam_id, question_id),
        KEY idx_exam_questions_exam_sort (exam_id, sort),
        CONSTRAINT fk_exam_questions_exam
            FOREIGN KEY (exam_id) REFERENCES exams (id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_exam_questions_question
            FOREIGN KEY (question_id) REFERENCES questions (id)
            ON DELETE SET NULL ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS exam_assignments (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        exam_id BIGINT UNSIGNED NOT NULL,
        employee_id BIGINT UNSIGNED NOT NULL,
        assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_exam_assignments_exam_employee (exam_id, employee_id),
        CONSTRAINT fk_exam_assignments_exam
            FOREIGN KEY (exam_id) REFERENCES exams (id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_exam_assignments_employee
            FOREIGN KEY (employee_id) REFERENCES employees (id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS exam_attempts (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        exam_id BIGINT UNSIGNED NOT NULL,
        employee_id BIGINT UNSIGNED NOT NULL,
        attempt_no INT NOT NULL DEFAULT 1,
        status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
        score DECIMAL(5,2) NULL,
        passed TINYINT(1) NULL,
        started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NULL,
        submitted_at DATETIME NULL,
        duration_seconds INT NULL,
        answers_json JSON NULL,
        PRIMARY KEY (id),
        UNIQUE KEY uk_exam_attempts_exam_employee_no (exam_id, employee_id, attempt_no),
        KEY idx_exam_attempts_exam_status (exam_id, status),
        CONSTRAINT fk_exam_attempts_exam
            FOREIGN KEY (exam_id) REFERENCES exams (id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_exam_attempts_employee
            FOREIGN KEY (employee_id) REFERENCES employees (id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS export_tasks (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        exam_id BIGINT UNSIGNED NULL,
        file_name VARCHAR(255) NOT NULL,
        export_type VARCHAR(30) NOT NULL DEFAULT '成绩明细',
        status VARCHAR(20) NOT NULL DEFAULT 'processing',
        row_count INT NOT NULL DEFAULT 0,
        file_path VARCHAR(500) NULL,
        expires_at DATETIME NULL,
        created_by VARCHAR(64) NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_export_tasks_tenant_created (tenant_code, created_at),
        CONSTRAINT fk_export_tasks_exam
            FOREIGN KEY (exam_id) REFERENCES exams (id)
            ON DELETE SET NULL ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS tenant_settings (
        tenant_code VARCHAR(64) NOT NULL,
        tenant_name VARCHAR(200) NOT NULL,
        admin_email VARCHAR(200) NULL,
        retention VARCHAR(50) NOT NULL DEFAULT '合同期 + 90 天',
        default_pass_score INT NOT NULL DEFAULT 60,
        default_duration INT NOT NULL DEFAULT 30,
        default_attempts INT NOT NULL DEFAULT 1,
        random_order VARCHAR(20) NOT NULL DEFAULT '随机',
        notify_assigned TINYINT(1) NOT NULL DEFAULT 1,
        notify_result TINYINT(1) NOT NULL DEFAULT 1,
        notify_deadline TINYINT(1) NOT NULL DEFAULT 0,
        notify_cards TINYINT(1) NOT NULL DEFAULT 0,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (tenant_code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS exam_knowledge_cards (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        exam_id BIGINT UNSIGNED NOT NULL,
        card_id BIGINT UNSIGNED NOT NULL,
        sort INT NOT NULL DEFAULT 0,
        PRIMARY KEY (id),
        UNIQUE KEY uk_exam_knowledge_cards_exam_card (exam_id, card_id),
        KEY idx_exam_knowledge_cards_exam_sort (exam_id, sort),
        CONSTRAINT fk_exam_knowledge_cards_exam
            FOREIGN KEY (exam_id) REFERENCES exams (id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_exam_knowledge_cards_card
            FOREIGN KEY (card_id) REFERENCES knowledge_cards (id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_card_views (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        employee_id BIGINT UNSIGNED NOT NULL,
        card_id BIGINT UNSIGNED NOT NULL,
        first_viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        view_count INT NOT NULL DEFAULT 1,
        PRIMARY KEY (id),
        UNIQUE KEY uk_knowledge_card_views_employee_card (employee_id, card_id),
        KEY idx_knowledge_card_views_tenant_card (tenant_code, card_id),
        CONSTRAINT fk_knowledge_card_views_employee
            FOREIGN KEY (employee_id) REFERENCES employees (id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_knowledge_card_views_card
            FOREIGN KEY (card_id) REFERENCES knowledge_cards (id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS wrong_questions (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        employee_id BIGINT UNSIGNED NOT NULL,
        question_id BIGINT UNSIGNED NULL,
        question_snapshot_json JSON NOT NULL,
        source_type VARCHAR(20) NOT NULL DEFAULT 'exam',
        source_id VARCHAR(64) NULL,
        wrong_count INT NOT NULL DEFAULT 1,
        correct_streak INT NOT NULL DEFAULT 0,
        last_wrong_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        mastered_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_wrong_questions_employee_question (employee_id, question_id),
        KEY idx_wrong_questions_tenant_employee_mastered (tenant_code, employee_id, mastered_at),
        CONSTRAINT fk_wrong_questions_employee
            FOREIGN KEY (employee_id) REFERENCES employees (id)
            ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_wrong_questions_question
            FOREIGN KEY (question_id) REFERENCES questions (id)
            ON DELETE SET NULL ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        recipient_type VARCHAR(20) NOT NULL,
        recipient_id BIGINT UNSIGNED NOT NULL,
        type VARCHAR(40) NOT NULL,
        title VARCHAR(200) NOT NULL,
        content VARCHAR(500) NOT NULL DEFAULT '',
        link_page VARCHAR(120) NOT NULL DEFAULT '',
        link_params VARCHAR(500) NOT NULL DEFAULT '',
        biz_type VARCHAR(30) NOT NULL DEFAULT '',
        biz_id BIGINT UNSIGNED NULL,
        read_at DATETIME NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uk_notifications_biz
            (recipient_type, recipient_id, type, biz_type, biz_id),
        KEY idx_notifications_unread (recipient_type, recipient_id, read_at, created_at),
        KEY idx_notifications_tenant_created (tenant_code, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
        tenant_code VARCHAR(64) NOT NULL DEFAULT 'demo',
        operator_id VARCHAR(64) NOT NULL DEFAULT '',
        operator_name VARCHAR(100) NOT NULL DEFAULT '',
        action VARCHAR(50) NOT NULL,
        target_type VARCHAR(50) NOT NULL DEFAULT '',
        target_id VARCHAR(64) NOT NULL DEFAULT '',
        detail_json JSON NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY idx_audit_tenant_created (tenant_code, created_at),
        KEY idx_audit_action (tenant_code, action, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS wechat_subscriptions (
        user_id BIGINT UNSIGNED NOT NULL,
        template_id VARCHAR(64) NOT NULL,
        remaining INT NOT NULL DEFAULT 0,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, template_id),
        CONSTRAINT fk_wechat_subscriptions_user
            FOREIGN KEY (user_id) REFERENCES users (id)
            ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


async def _ensure_column(cursor, table: str, column: str, ddl: str) -> None:
    await cursor.execute(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
        (table, column),
    )
    row = await cursor.fetchone()
    if row and int(row[0]) == 0:
        await cursor.execute(ddl)


async def _ensure_index(cursor, table: str, index_name: str, ddl: str) -> None:
    await cursor.execute(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() AND table_name = %s AND index_name = %s",
        (table, index_name),
    )
    row = await cursor.fetchone()
    if row and int(row[0]) == 0:
        await cursor.execute(ddl)


async def init_mysql() -> None:
    """初始化数据库与基础表结构。"""
    global _pool

    if _pool is not None:
        return

    settings = get_settings()

    bootstrap_conn = await aiomysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        charset=settings.mysql_charset,
        autocommit=True,
    )
    try:
        async with bootstrap_conn.cursor() as cursor:
            await cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                f"CHARACTER SET {settings.mysql_charset} COLLATE utf8mb4_unicode_ci"
            )
    finally:
        bootstrap_conn.close()

    _pool = await aiomysql.create_pool(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        db=settings.mysql_database,
        charset=settings.mysql_charset,
        minsize=settings.mysql_pool_minsize,
        maxsize=settings.mysql_pool_maxsize,
        autocommit=True,
    )

    async with _pool.acquire() as conn:
        async with conn.cursor() as cursor:
            for statement in SCHEMA_STATEMENTS:
                await cursor.execute(statement)
            await _ensure_column(
                cursor,
                "exam_attempts",
                "expires_at",
                "ALTER TABLE exam_attempts ADD COLUMN expires_at DATETIME NULL AFTER started_at",
            )
            await _ensure_column(
                cursor,
                "exam_attempts",
                "answers_json",
                "ALTER TABLE exam_attempts ADD COLUMN answers_json JSON NULL AFTER duration_seconds",
            )
            await _ensure_column(
                cursor,
                "knowledge_cards",
                "doc_id",
                "ALTER TABLE knowledge_cards ADD COLUMN doc_id BIGINT UNSIGNED NULL AFTER tenant_code",
            )
            await _ensure_column(
                cursor,
                "employees",
                "user_id",
                "ALTER TABLE employees ADD COLUMN user_id BIGINT UNSIGNED NULL AFTER org_id",
            )
            await _ensure_index(
                cursor,
                "employees",
                "uk_employees_user",
                "ALTER TABLE employees ADD UNIQUE KEY uk_employees_user (user_id)",
            )
            await _ensure_column(
                cursor,
                "employees",
                "notify_deadline",
                "ALTER TABLE employees ADD COLUMN notify_deadline TINYINT(1) NOT NULL DEFAULT 1 AFTER status",
            )
            await _ensure_column(
                cursor,
                "questions",
                "deleted_at",
                "ALTER TABLE questions ADD COLUMN deleted_at DATETIME NULL AFTER reviewed_at",
            )
            await _ensure_column(
                cursor,
                "exams",
                "description",
                "ALTER TABLE exams ADD COLUMN description TEXT NULL AFTER title",
            )
            await _ensure_column(
                cursor,
                "export_tasks",
                "expires_at",
                "ALTER TABLE export_tasks ADD COLUMN expires_at DATETIME NULL AFTER file_path",
            )

    logger.info("mysql_initialized", database=settings.mysql_database)


def get_mysql_pool() -> aiomysql.Pool | None:
    return _pool


async def close_mysql_pool() -> None:
    global _pool

    if _pool is None:
        return

    _pool.close()
    await _pool.wait_closed()
    _pool = None
    logger.info("mysql_pool_closed")
