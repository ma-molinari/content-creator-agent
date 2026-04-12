#!/usr/bin/env bash
# Syncs canonical Cursor rules/skills into backend/internal/agent/promptdata/ and strips YAML frontmatter.
# Run from repo root after editing files under .cursor/: ./scripts/sync-promptdata.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/backend/internal/agent/promptdata"

strip_frontmatter() {
  # Skips first --- ... --- block if the file starts with YAML frontmatter.
  awk '
    BEGIN { fm = 0 }
    /^---$/ {
      if (fm == 0) { fm = 1; next }
      if (fm == 1) { fm = 2; next }
    }
    fm == 1 { next }
    { print }
  '
}

copy_stripped() {
  local src="$1"
  local dest_name="$2"
  if [[ ! -f "$src" ]]; then
    echo "sync-promptdata: missing source: $src" >&2
    exit 1
  fi
  strip_frontmatter < "$src" > "$DEST/$dest_name"
  echo "sync-promptdata: wrote $dest_name"
}

mkdir -p "$DEST"

copy_stripped "$ROOT/.cursor/skills/create-social-posts/SKILL.md" "create-social-posts_skill.md"
copy_stripped "$ROOT/.cursor/skills/create-social-posts/context-checklist.md" "context-checklist.md"
copy_stripped "$ROOT/.cursor/rules/social-media/instagram-feed.md" "instagram-feed.md"
copy_stripped "$ROOT/.cursor/rules/social-media/image-designer.md" "image-designer.md"
copy_stripped "$ROOT/.cursor/rules/design/design-ui-designer.md" "design-ui-designer.md"
copy_stripped "$ROOT/.cursor/rules/marketing/marketing-carousel-growth-engine.md" "marketing-carousel-growth-engine.md"

echo "sync-promptdata: done (manual files: api_carousel_context.md, optimizer_instructions.md, slide_output_format.md)"
