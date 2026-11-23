ALTER TABLE jobs ADD COLUMN target_schema_version INTEGER;
ALTER TABLE jobs ADD CONSTRAINT jobs_target_schema_version_check
    CHECK (target_schema_version IS NULL OR target_schema_version IN (1, 2));
