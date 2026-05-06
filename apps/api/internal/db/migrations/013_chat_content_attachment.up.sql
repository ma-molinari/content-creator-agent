CREATE TABLE chat_content_attachment (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_content_id UUID NOT NULL REFERENCES chat_content(id) ON DELETE CASCADE,
    s3_key          VARCHAR(512) NOT NULL,
    mime_type       VARCHAR(64)  NOT NULL,
    size_bytes      BIGINT       NOT NULL,
    sort_order      INT          NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_content_attachment_content_id ON chat_content_attachment(chat_content_id);
