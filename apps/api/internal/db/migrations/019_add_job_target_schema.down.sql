DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM jobs WHERE target_schema_version = 2)
        OR EXISTS (SELECT 1 FROM post_versions WHERE schema_version = 2) THEN
        RAISE EXCEPTION 'cannot remove job target schema while V2 data exists';
    END IF;
END $$;
ALTER TABLE jobs DROP CONSTRAINT jobs_target_schema_version_check;
ALTER TABLE jobs DROP COLUMN target_schema_version;
