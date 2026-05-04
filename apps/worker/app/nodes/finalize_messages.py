"""User-facing finalize callback messages (Portuguese — API persists these for the UI)."""

# Partial / interrupt delivery after uploads were attempted — no internal echoes.
JOB_FAILURE_INCOMPLETE_CAROUSEL = (
    "A geração do carrossel não foi concluída corretamente. Tente novamente."
)

# Early pipeline failures (parse, brief, etc.) — no internal echoes.
JOB_FAILURE_GENERIC = "Não foi possível concluir seu conteúdo. Tente novamente."

# HTML artefact mandatory (REQUIRE_HTML_ARTIFACT_UPLOAD) but missing after upload_assets.
JOB_FAILURE_HTML_ARTIFACT = (
    "Não foi possível guardar os ficheiros fonte dos slides. Tente novamente."
)

# Mirrors nested error callback sent when HTTP delivery fails.
JOB_FAILURE_CALLBACK_TRANSPORT = "callback delivery failed"
