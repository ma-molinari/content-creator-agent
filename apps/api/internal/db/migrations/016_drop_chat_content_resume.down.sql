CREATE TABLE chat_content_resume (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id         UUID NOT NULL UNIQUE REFERENCES chats(id) ON DELETE CASCADE,
    summary         TEXT,
    last_content_at TIMESTAMPTZ,
    summarized_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_chat_content_resume_chat_id ON chat_content_resume (chat_id);
