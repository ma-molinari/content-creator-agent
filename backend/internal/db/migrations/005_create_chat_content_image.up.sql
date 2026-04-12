CREATE TABLE chat_content_image (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_content_id UUID NOT NULL REFERENCES chat_content (id) ON DELETE CASCADE,
    s3_key VARCHAR(512) NOT NULL,
    url VARCHAR(1024) NOT NULL,
    slide_number INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_content_image_chat_content_id ON chat_content_image (chat_content_id);
