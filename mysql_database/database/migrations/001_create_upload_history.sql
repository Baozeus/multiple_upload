-- UDM_10 metadata schema for MySQL 8.0+.
-- Safe bootstrap only: no DROP, TRUNCATE, DELETE, or BLOB columns.

CREATE DATABASE IF NOT EXISTS `udm_10`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE `udm_10`;

CREATE TABLE IF NOT EXISTS upload_batches (
    id VARCHAR(64) NOT NULL,
    started_at DATETIME(6) NOT NULL,
    completed_at DATETIME(6) NULL,
    PRIMARY KEY (id),
    INDEX idx_upload_batches_started_at (started_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS upload_files (
    id VARCHAR(64) NOT NULL,
    batch_id VARCHAR(64) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    stored_name VARCHAR(255) NULL,
    size_bytes BIGINT UNSIGNED NOT NULL,
    status VARCHAR(32) NOT NULL,
    duplicate_policy VARCHAR(16) NULL,
    error_message TEXT NULL,
    started_at DATETIME(6) NOT NULL,
    completed_at DATETIME(6) NULL,
    relative_path VARCHAR(512) NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_upload_files_batch
        FOREIGN KEY (batch_id) REFERENCES upload_batches(id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT chk_upload_files_status
        CHECK (status IN ('waiting', 'uploading', 'completed', 'failed', 'skipped')),
    CONSTRAINT chk_upload_files_duplicate_policy
        CHECK (duplicate_policy IS NULL OR duplicate_policy IN ('overwrite', 'rename', 'skip')),
    INDEX idx_upload_files_batch (batch_id),
    INDEX idx_upload_files_status_completed (status, completed_at),
    INDEX idx_upload_files_original_name (original_name),
    INDEX idx_upload_files_stored_name (stored_name)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS upload_events (
    id VARCHAR(64) NOT NULL,
    file_id VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL,
    message TEXT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_upload_events_file
        FOREIGN KEY (file_id) REFERENCES upload_files(id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    INDEX idx_upload_events_file_created (file_id, created_at)
) ENGINE=InnoDB;
