ALTER TABLE chats ADD COLUMN post_format VARCHAR(32) NOT NULL DEFAULT 'legacy_html'
    CHECK (post_format IN ('legacy_html', 'structured_v1'));
ALTER TABLE chats ADD COLUMN current_version_id UUID;
ALTER TABLE jobs ADD COLUMN post_format VARCHAR(32) NOT NULL DEFAULT 'legacy_html'
    CHECK (post_format IN ('legacy_html', 'structured_v1'));
ALTER TABLE jobs ADD COLUMN generation_mode VARCHAR(16)
    CHECK (generation_mode IS NULL OR generation_mode IN ('create', 'edit'));
ALTER TABLE jobs ADD COLUMN expected_version_id UUID;

ALTER TABLE jobs ADD CONSTRAINT jobs_id_chat_unique UNIQUE (id, chat_id);
ALTER TABLE chat_content ADD CONSTRAINT chat_content_id_chat_unique UNIQUE (id, chat_id);

CREATE TABLE post_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    job_id UUID NOT NULL UNIQUE,
    assistant_content_id UUID NOT NULL UNIQUE,
    parent_version_id UUID,
    document_s3_key VARCHAR(512) NOT NULL CHECK (length(trim(document_s3_key)) > 0),
    schema_version INTEGER NOT NULL CHECK (schema_version > 0),
    renderer_version VARCHAR(64) NOT NULL CHECK (length(trim(renderer_version)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT post_versions_id_chat_unique UNIQUE (id, chat_id),
    CONSTRAINT post_versions_job_chat_fk FOREIGN KEY (job_id, chat_id)
        REFERENCES jobs(id, chat_id) ON DELETE CASCADE,
    CONSTRAINT post_versions_content_chat_fk FOREIGN KEY (assistant_content_id, chat_id)
        REFERENCES chat_content(id, chat_id) ON DELETE CASCADE,
    CONSTRAINT post_versions_parent_chat_fk FOREIGN KEY (parent_version_id, chat_id)
        REFERENCES post_versions(id, chat_id) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT post_versions_no_self_parent CHECK (parent_version_id IS NULL OR parent_version_id <> id)
);

ALTER TABLE chats ADD CONSTRAINT chats_current_version_fk
    FOREIGN KEY (current_version_id, id) REFERENCES post_versions(id, chat_id)
    DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE jobs ADD CONSTRAINT jobs_expected_version_fk
    FOREIGN KEY (expected_version_id, chat_id) REFERENCES post_versions(id, chat_id)
    DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX post_versions_chat_created_idx ON post_versions(chat_id, created_at);
