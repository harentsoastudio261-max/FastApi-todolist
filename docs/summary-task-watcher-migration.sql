-- Summary task watcher migration for an existing MySQL database.
-- Run this once if the tables already existed before the watcher feature.

ALTER TABLE summary_task
    ADD COLUMN status ENUM('pending', 'processing', 'processed', 'failed') NOT NULL DEFAULT 'pending',
    ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN processing_started_at DATETIME NULL,
    ADD COLUMN processed_at DATETIME NULL,
    ADD COLUMN processing_error VARCHAR(1000) NULL;

CREATE INDEX ix_summary_task_status ON summary_task (status);

ALTER TABLE tasks
    ADD COLUMN source_summary_task_id INT NULL,
    ADD INDEX ix_tasks_source_summary_task_id (source_summary_task_id),
    ADD CONSTRAINT fk_tasks_source_summary_task_id
        FOREIGN KEY (source_summary_task_id) REFERENCES summary_task(id)
        ON DELETE SET NULL,
    ADD CONSTRAINT uq_tasks_user_summary_task UNIQUE (user_id, source_summary_task_id);
