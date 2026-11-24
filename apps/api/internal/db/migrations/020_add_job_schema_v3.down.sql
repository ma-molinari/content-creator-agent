DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM jobs WHERE target_schema_version = 3)
        OR EXISTS (SELECT 1 FROM post_versions WHERE schema_version = 3) THEN
        RAISE EXCEPTION 'cannot roll back schema V3 while V3 jobs or versions exist';
    END IF;
END $$;
ALTER TABLE jobs DROP CONSTRAINT jobs_target_schema_version_check;
ALTER TABLE jobs ADD CONSTRAINT jobs_target_schema_version_check
    CHECK (target_schema_version IS NULL OR target_schema_version IN (1, 2));
