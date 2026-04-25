# Code Conventions

## Go API (`apps/api`)

### Naming Conventions

**Packages:** lowercase single-word names matching directory names.
Examples: `auth`, `chat`, `jobs`, `middleware`, `httperr`

**Files:** `<role>.go` — one clear role per file.
Examples: `handler.go`, `service.go`, `repository.go`, `models.go`, `config.go`, `slide_key.go`

**Types / structs:** PascalCase.
Examples: `Service`, `Repository`, `Handler`, `Config`, `CompleteBody`, `ArtifactRef`, `ServiceError`

**Constructor functions:** `NewXxx(deps…) *Xxx`.
Examples: `NewService(repo, jwtSecret, ...)`, `NewHandler(svc)`, `NewRepository(gdb)`

**Methods:** receiver-based, camelCase verb.
Examples: `(s *Service) Register(...)`, `(h *Handler) Complete(...)`, `(r *Repository) FindByEmail(...)`

**Private helpers:** camelCase prefixed with `err` for error factories.
Examples: `errStatus(status, msg)`, `mapChatErr(err)`, `mapPostErr(err)`

**Constants:** camelCase for unexported, PascalCase for exported.
Examples: `bcryptCost`, `accessTokenTTL`, `workerAPIKeyHeader`, `UserIDKey`, `ErrInvalidSlideS3Key`

### Import ordering

Standard library → external packages → internal packages, separated by blank lines.

```go
import (
    "context"
    "net/http"

    "github.com/google/uuid"
    "github.com/labstack/echo/v4"
    "gorm.io/gorm"

    "content-creator-agent/internal/db"
    "content-creator-agent/internal/httperr"
)
```

### Error handling

- Repository layer: translate `gorm.ErrRecordNotFound` to `nil, nil` (caller checks nil pointer).
- Service layer: return domain sentinel errors (`ErrNotFound`, `ErrForbidden`) or `*ServiceError{HTTPStatus, Message}` for user-visible errors; surface raw errors only to logs.
- Handler layer: map service errors to `echo.HTTPError` via `mapXxxErr()` helpers; never expose internal error messages to clients.
- Internal errors: always `httperr.Internal(prefix, err)` — logs the real error, returns generic `500 "internal error"`.

```go
// Repository returns nil for not-found:
if errors.Is(err, gorm.ErrRecordNotFound) {
    return nil, nil
}

// Service returns typed sentinel:
return nil, errStatus(http.StatusConflict, "email already registered")

// Handler maps to HTTP:
func mapChatErr(err error) *echo.HTTPError {
    switch {
    case errors.Is(err, ErrNotFound):  return echo.NewHTTPError(404, "not found")
    case errors.Is(err, ErrForbidden): return echo.NewHTTPError(403, "forbidden")
    default: return httperr.Internal("[chat]", err)
    }
}
```

### Database conventions

- GORM models in `internal/db/models.go`; each model has explicit `TableName()`.
- All primary keys are `uuid.UUID` with `gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`.
- Enum types declared in PostgreSQL via migration `001_create_enums.up.sql`; referenced with `gorm:"type:xxx_enum"`.
- Transactions: `gdb.WithContext(ctx).Transaction(func(tx *gorm.DB) error { … })`.
- Repositories hold `*gorm.DB` and always pass `ctx` via `.WithContext(ctx)`.

### JSON response conventions

- Handlers define private `xxxJSON` structs for wire format; never serialize ORM models directly.
- `omitempty` on optional pointer fields (`*string`, `*time.Time`, slice).
- Verb in response body minimized; status codes carry semantic meaning.

### Test conventions (unit)

- File: `<unit>_test.go` in same package.
- SQLite in-memory DB for repo-level tests (`"sqlite::memory:?cache=shared"`).
- Testify `require.*` for hard assertions; `assert.*` for soft assertions.
- Table-driven tests where multiple cases share the same fixture.

---

## Python Worker (`apps/worker`)

### Naming conventions

**Files / modules:** snake_case.
Examples: `generate_slides.py`, `render_to_jpeg.py`, `parse_validate.py`

**Classes:** PascalCase.
Examples: `DispatchPayload`, `AgentState`, `SlideItem`, `RenderedSlide`

**Functions / variables:** snake_case.
Examples: `build_graph()`, `_initial_state()`, `load_profile()`, `render_to_jpeg()`

**Private helpers:** prefixed with `_`.
Examples: `_read_generate_prompt()`, `_initial_state()`, `_run_job()`

### Node pattern

Each LangGraph node is a plain async or sync function accepting `AgentState` and returning a `dict` of state updates. Nodes are collected in `app/nodes/`, imported by name into `app/graph.py`.

```python
async def render_to_jpeg(state: AgentState) -> dict:
    logger.info("node=render_to_jpeg job_id=%s", state.get("job_id"))
    ...
    return {"rendered_slides": rendered, "errors": errors}
```

### State typing

`AgentState` is a flat `TypedDict`; optional fields use `NotRequired`. Nodes only return the keys they modify.

### Logging

Module-level `logger = logging.getLogger(__name__)`. Log every node entry with `node=<name> job_id=<id>`.

### Error handling

Errors per slide/step are accumulated in `state["errors"]` list rather than raising. Fatal errors bubble up and are caught by the job runner in `main.py`, which logs the exception without crashing the server.

---

## TypeScript / React SPA (`apps/web`)

### Naming conventions

**Files:** PascalCase for components and pages (`ChatThread.tsx`, `Login.tsx`), camelCase for utilities and API modules (`client.ts`, `auth.ts`, `queryClient.ts`).

**Components:** PascalCase function components with named export.
Examples: `export function ChatThread()`, `export const ComposerBar`

**Hooks / stores:** camelCase prefixed with `use`.
Examples: `useAuthStore`, `useQueryClient`

**API modules:** grouped by domain, returning typed responses via axios.
Examples: `apps/web/src/api/auth.ts`, `apps/web/src/api/chats.ts`

### State management split

- **Server state:** TanStack React Query (fetch, cache, invalidate)
- **Global client state:** Zustand stores (`src/stores/auth.ts`)
- **Local component state:** `useState` / `useReducer`

### Auth token convention

Access token lives **in-memory only** (Zustand, never `localStorage`). Refresh token travels as HttpOnly cookie. Axios interceptor handles silent refresh + request retry.

### Import aliasing

`@/` maps to `src/` (configured in `tsconfig.app.json` and `vite.config.ts`).
Examples: `import { api } from '@/api/client'`, `import { useAuthStore } from '@/stores/auth'`

### Comments / documentation

Comments are used sparingly — only for non-obvious design decisions.
Examples:
```ts
/** Access token only in memory — never persist (see design). */
export const useAuthStore = …

// 401 → refresh → retry once → clear + redirect
```
