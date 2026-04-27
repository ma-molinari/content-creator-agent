CREATE TABLE login_attempts (
    user_id   UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ON login_attempts (user_id, failed_at);
