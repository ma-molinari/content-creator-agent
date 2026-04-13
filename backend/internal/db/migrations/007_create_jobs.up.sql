CREATE TYPE job_status_enum AS ENUM ('pending', 'processing', 'done', 'failed');

CREATE TABLE jobs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id     UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status      job_status_enum NOT NULL DEFAULT 'pending',
    error_msg   TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_jobs_chat_id ON jobs (chat_id);
CREATE INDEX idx_jobs_user_id ON jobs (user_id);
