ALTER TABLE jobs ADD COLUMN stage VARCHAR(64) NOT NULL DEFAULT 'queued';
ALTER TABLE jobs ADD COLUMN progress INTEGER NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD CONSTRAINT jobs_progress_range CHECK (progress >= 0 AND progress <= 100);
ALTER TABLE jobs ADD COLUMN heartbeat_at TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN error_code VARCHAR(64);

UPDATE jobs
SET
    stage = CASE status
        WHEN 'pending' THEN 'queued'
        WHEN 'processing' THEN 'processing'
        WHEN 'done' THEN 'done'
        WHEN 'failed' THEN 'failed'
        ELSE 'queued'
    END,
    progress = CASE status
        WHEN 'done' THEN 100
        WHEN 'failed' THEN 100
        ELSE progress
    END;
