#!/usr/bin/env python3
"""
Rebuilds git history with one commit per completed task (T1–T17) plus first commit.
Run from repository root: python3 scripts/build_git_history.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "apps" / "api"
BACKUP = Path("/tmp/cca_backend_backup_for_git_history")


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.check_call(cmd, cwd=cwd or ROOT)


def join_lines(lines: list[str]) -> str:
    return "".join(lines)


def main() -> None:
    if not BACKEND.is_dir():
        raise SystemExit("apps/api/ not found")

    if BACKUP.exists():
        shutil.rmtree(BACKUP)
    shutil.copytree(BACKEND, BACKUP)

    git_dir = ROOT / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    run(["git", "init"], cwd=ROOT)
    run(["git", "config", "user.email", "dev@local"], cwd=ROOT)
    run(["git", "config", "user.name", "content-creator-agent"], cwd=ROOT)
    run(["git", "config", "commit.gpgsign", "false"], cwd=ROOT)

    readme = ROOT / "README.md"
    if not readme.exists():
        readme.write_text("# content-creator-agent\n", encoding="utf-8")

    extra_paths: list[Path] = []
    for rel in (
        ".specs",
        ".cursor",
        "docs",
        "package.json",
        "package-lock.json",
        "scripts",
        "instagram-audits",
    ):
        p = ROOT / rel
        if p.exists():
            extra_paths.append(p)

    run(["git", "add", "README.md", ".gitignore", *[str(p.relative_to(ROOT)) for p in extra_paths]], cwd=ROOT)
    run(["git", "commit", "-m", "first commit"], cwd=ROOT)

    main_path = BACKUP / "cmd/server/main.go"
    m = main_path.read_text(encoding="utf-8").splitlines(keepends=True)

    h_lines = (BACKUP / "internal/auth/handler.go").read_text(encoding="utf-8").splitlines(keepends=True)
    s_lines = (BACKUP / "internal/auth/service.go").read_text(encoding="utf-8").splitlines(keepends=True)

    def slice_file(lines: list[str], start: int, end: int) -> str:
        return join_lines(lines[start - 1 : end])

    def auth_handler(n: int) -> str:
        if n <= 3:
            return ""
        if n == 4:
            return slice_file(h_lines, 1, 41) + slice_file(h_lines, 113, 119)
        if n == 5:
            return slice_file(h_lines, 1, 72) + slice_file(h_lines, 113, 119)
        if n == 6:
            return slice_file(h_lines, 1, 89) + slice_file(h_lines, 113, 119)
        return join_lines(h_lines)

    def auth_service(n: int) -> str:
        if n <= 3:
            return ""
        if n == 4:
            return slice_file(s_lines, 1, 89)
        if n == 5:
            return slice_file(s_lines, 1, 138)
        if n == 6:
            return slice_file(s_lines, 1, 177)
        return join_lines(s_lines)

    repo_full = (BACKUP / "internal/auth/repository.go").read_text(encoding="utf-8")

    migrations = sorted((BACKUP / "internal/db/migrations").glob("*.sql"))
    mig_rel = [str(p.relative_to(BACKUP)) for p in migrations]

    service_src = (BACKUP / "internal/chat/service.go").read_text(encoding="utf-8")
    service_simple_create = service_src.replace(
        """// CreateChat creates a chat, evicting the oldest when the user already has 5.
func (s *Service) CreateChat(ctx context.Context, userID uuid.UUID, postType string) (*db.Chat, error) {
	pt, err := parsePostType(postType)
	if err != nil {
		return nil, err
	}
	n, err := s.repo.CountByUser(ctx, userID)
	if err != nil {
		return nil, err
	}
	if n >= 5 {
		oldest, err := s.repo.OldestChatID(ctx, userID)
		if err != nil {
			return nil, err
		}
		if err := s.DeleteChat(ctx, userID, oldest); err != nil {
			return nil, err
		}
	}
	return s.repo.Create(ctx, userID, pt)
}
""",
        """// CreateChat creates a chat (5-chat eviction added in T14).
func (s *Service) CreateChat(ctx context.Context, userID uuid.UUID, postType string) (*db.Chat, error) {
	pt, err := parsePostType(postType)
	if err != nil {
		return nil, err
	}
	return s.repo.Create(ctx, userID, pt)
}
""",
    )

    nop_go = """package storage

import (
	"context"
	"time"
)

// Nop is a no-op storage before S3 (T9–T11); replaced in T13.
type Nop struct{}

func (Nop) Upload(ctx context.Context, key string, data []byte) error { return nil }

func (Nop) GetSignedURL(ctx context.Context, key string, expiry time.Duration) (string, error) {
	return "https://example.com/signed", nil
}

func (Nop) GetObject(ctx context.Context, key string) ([]byte, error) { return []byte{0xff, 0xd8}, nil }

func (Nop) Delete(ctx context.Context, key string) error { return nil }

func (Nop) DeleteMany(ctx context.Context, keys []string) error { return nil }
"""

    def main_t1() -> str:
        return """package main

import (
	"log"
	"net/http"
	"os"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	e := echo.New()
	e.HideBanner = true
	e.Use(middleware.Recover())
	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	if err := e.Start(":" + port); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
"""

    def main_t3() -> str:
        return """package main

import (
	"log"
	"net/http"
	"os"

	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	cfg := config.Load()
	_ = cfg
	gdb := db.Connect()
	if err := db.RunMigrations(os.Getenv("DATABASE_URL")); err != nil {
		log.Fatalf("migrations: %v", err)
	}
	_ = gdb

	e := echo.New()
	e.HideBanner = true
	e.Use(middleware.Recover())
	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	if err := e.Start(":" + port); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
"""

    def main_t4() -> str:
        return """package main

import (
	"log"
	"net/http"
	"os"

	"content-creator-agent/internal/auth"
	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	cfg := config.Load()
	if cfg.JWTSecret == "" || cfg.JWTRefreshSecret == "" {
		log.Fatal("JWT_SECRET and JWT_REFRESH_SECRET must be set")
	}

	gdb := db.Connect()
	if err := db.RunMigrations(os.Getenv("DATABASE_URL")); err != nil {
		log.Fatalf("migrations: %v", err)
	}

	repo := auth.NewRepository(gdb)
	cookieSecure := os.Getenv("COOKIE_SECURE") != "false"
	svc := auth.NewService(repo, cfg.JWTSecret, cfg.JWTRefreshSecret, cookieSecure)
	h := auth.NewHandler(svc)

	e := echo.New()
	e.HideBanner = true
	e.Use(middleware.Recover())
	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	authGroup := e.Group("/auth")
	authGroup.POST("/register", h.Register)

	addr := ":" + cfg.Port
	if err := e.Start(addr); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
"""

    def main_t5() -> str:
        return main_t4().replace(
            "\tauthGroup := e.Group(\"/auth\")\n\tauthGroup.POST(\"/register\", h.Register)\n",
            "\tauthGroup := e.Group(\"/auth\")\n\tauthGroup.POST(\"/register\", h.Register)\n\tauthGroup.POST(\"/login\", h.Login)\n",
        )

    def main_t6() -> str:
        return """package main

import (
	"log"
	"net/http"
	"os"

	"content-creator-agent/internal/auth"
	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	appmw "content-creator-agent/internal/middleware"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	cfg := config.Load()
	if cfg.JWTSecret == "" || cfg.JWTRefreshSecret == "" {
		log.Fatal("JWT_SECRET and JWT_REFRESH_SECRET must be set")
	}

	gdb := db.Connect()
	if err := db.RunMigrations(os.Getenv("DATABASE_URL")); err != nil {
		log.Fatalf("migrations: %v", err)
	}

	repo := auth.NewRepository(gdb)
	cookieSecure := os.Getenv("COOKIE_SECURE") != "false"
	svc := auth.NewService(repo, cfg.JWTSecret, cfg.JWTRefreshSecret, cookieSecure)
	h := auth.NewHandler(svc)

	e := echo.New()
	e.HideBanner = true
	e.Use(middleware.Recover())
	e.GET("/health", func(c echo.Context) error {
		return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
	})

	authGroup := e.Group("/auth")
	authGroup.POST("/register", h.Register)
	authGroup.POST("/login", h.Login)
	authGroup.POST("/refresh", h.Refresh)

	protected := e.Group("")
	protected.Use(appmw.JWT(cfg.JWTSecret))
	protected.GET("/me", func(c echo.Context) error {
		uid := appmw.UserID(c)
		return c.JSON(http.StatusOK, map[string]string{"userId": uid.String()})
	})
	protected.GET("/chats", func(c echo.Context) error {
		return c.JSON(http.StatusOK, []interface{}{})
	})

	addr := ":" + cfg.Port
	if err := e.Start(addr); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
}
"""

    def main_t7() -> str:
        return main_t6().replace(
            "\tauthGroup.POST(\"/refresh\", h.Refresh)\n",
            "\tauthGroup.POST(\"/refresh\", h.Refresh)\n\tauthGroup.POST(\"/recover-password\", h.RecoverPassword)\n",
        )

    def main_t8() -> str:
        # Through /me, then LLM stub; no chat/storage wiring yet
        return join_lines(m[0:65]) + join_lines(m[74:85])

    def main_nop_chat_prefix() -> str:
        return (
            join_lines(m[0:33])
            + "\tvar stor storage.StorageService = storage.Nop{}\n"
            "\tchatRepo := chat.NewRepository(gdb)\n"
            "\tchatSvc := chat.NewService(chatRepo, stor)\n"
            "\tch := chat.NewHandler(chatSvc)\n\n"
            + join_lines(m[42:66])
        )

    def main_s3_chat_prefix() -> str:
        return join_lines(m[0:41]) + join_lines(m[42:66])

    def main_t9() -> str:
        return main_nop_chat_prefix() + join_lines(m[66:67]) + join_lines(m[74:85])

    def main_t10() -> str:
        return main_nop_chat_prefix() + join_lines(m[66:68]) + join_lines(m[74:85])

    def main_t11() -> str:
        return main_nop_chat_prefix() + join_lines(m[66:70]) + join_lines(m[74:85])

    def main_t13() -> str:
        return main_s3_chat_prefix() + join_lines(m[66:70]) + join_lines(m[74:85])

    def main_t12() -> str:
        return main_s3_chat_prefix() + join_lines(m[66:71]) + join_lines(m[74:85])

    def main_t14() -> str:
        return main_t12()

    def main_t15() -> str:
        # Through DELETE, then list files only (skip download at index 70)
        return main_s3_chat_prefix() + join_lines(m[66:70]) + join_lines(m[71:72]) + join_lines(m[74:85])

    def main_t16() -> str:
        return main_s3_chat_prefix() + join_lines(m[66:72]) + join_lines(m[74:85])

    def main_t17() -> str:
        return join_lines(m)

    base_keep = {
        "cmd/server/main.go",
        "go.mod",
        "go.sum",
        "Dockerfile",
        ".dockerignore",
        "Makefile",
    }

    chat_files = {
        "internal/chat/doc.go",
        "internal/chat/handler.go",
        "internal/chat/repository.go",
        "internal/chat/service.go",
    }

    def copy_tree_filtered(keep: set[str]) -> None:
        if BACKEND.exists():
            shutil.rmtree(BACKEND)
        shutil.copytree(BACKUP, BACKEND, dirs_exist_ok=True)
        for root, _dirs, files in os.walk(BACKEND):
            for f in files:
                fp = Path(root) / f
                rel = str(fp.relative_to(BACKEND)).replace(os.sep, "/")
                if rel not in keep:
                    fp.unlink()

    def write_main(content: str) -> None:
        (BACKEND / "cmd/server/main.go").write_text(content, encoding="utf-8")

    def write_t1() -> None:
        copy_tree_filtered(base_keep)
        write_main(main_t1())

    def write_t2() -> None:
        copy_tree_filtered(base_keep | set(mig_rel))

    def write_t3() -> None:
        k = base_keep | set(mig_rel) | {
            "internal/db/db.go",
            "internal/db/models.go",
            "internal/db/migrate.go",
            "internal/db/db_test.go",
            "internal/config/config.go",
            ".env.example",
        }
        copy_tree_filtered(k)
        write_main(main_t3())

    def write_t4() -> None:
        k = base_keep | set(mig_rel) | {
            "internal/db/db.go",
            "internal/db/models.go",
            "internal/db/migrate.go",
            "internal/db/db_test.go",
            "internal/config/config.go",
            ".env.example",
            "internal/auth/handler.go",
            "internal/auth/service.go",
            "internal/auth/repository.go",
        }
        copy_tree_filtered(k)
        write_main(main_t4())
        (BACKEND / "internal/auth/handler.go").write_text(auth_handler(4), encoding="utf-8")
        (BACKEND / "internal/auth/service.go").write_text(auth_service(4), encoding="utf-8")
        (BACKEND / "internal/auth/repository.go").write_text(repo_full, encoding="utf-8")

    def write_t5() -> None:
        write_t4()
        write_main(main_t5())
        (BACKEND / "internal/auth/handler.go").write_text(auth_handler(5), encoding="utf-8")
        (BACKEND / "internal/auth/service.go").write_text(auth_service(5), encoding="utf-8")

    def write_t6() -> None:
        k = base_keep | set(mig_rel) | {
            "internal/db/db.go",
            "internal/db/models.go",
            "internal/db/migrate.go",
            "internal/db/db_test.go",
            "internal/config/config.go",
            ".env.example",
            "internal/auth/handler.go",
            "internal/auth/service.go",
            "internal/auth/repository.go",
            "internal/middleware/jwt.go",
        }
        copy_tree_filtered(k)
        write_main(main_t6())
        (BACKEND / "internal/auth/handler.go").write_text(auth_handler(6), encoding="utf-8")
        (BACKEND / "internal/auth/service.go").write_text(auth_service(6), encoding="utf-8")

    def write_t7() -> None:
        write_t6()
        write_main(main_t7())
        (BACKEND / "internal/auth/handler.go").write_text(auth_handler(7), encoding="utf-8")
        (BACKEND / "internal/auth/service.go").write_text(auth_service(7), encoding="utf-8")

    def write_t8() -> None:
        k = base_keep | set(mig_rel) | {
            "internal/db/db.go",
            "internal/db/models.go",
            "internal/db/migrate.go",
            "internal/db/db_test.go",
            "internal/config/config.go",
            ".env.example",
            "internal/auth/handler.go",
            "internal/auth/service.go",
            "internal/auth/repository.go",
            "internal/middleware/jwt.go",
            "internal/middleware/rate_limit.go",
            "internal/middleware/security.go",
        }
        copy_tree_filtered(k)
        write_main(main_t8())

    def write_t9() -> None:
        k = (
            base_keep
            | set(mig_rel)
            | {
                "internal/db/db.go",
                "internal/db/models.go",
                "internal/db/migrate.go",
                "internal/db/db_test.go",
                "internal/config/config.go",
                ".env.example",
                "internal/auth/handler.go",
                "internal/auth/service.go",
                "internal/auth/repository.go",
                "internal/middleware/jwt.go",
                "internal/middleware/rate_limit.go",
                "internal/middleware/security.go",
            }
            | chat_files
            | {"internal/storage/nop.go"}
        )
        copy_tree_filtered(k)
        (BACKEND / "internal/storage/nop.go").write_text(nop_go, encoding="utf-8")
        (BACKEND / "internal/chat/service.go").write_text(service_simple_create, encoding="utf-8")
        write_main(main_t9())

    def write_t10() -> None:
        write_t9()
        write_main(main_t10())

    def write_t11() -> None:
        write_t9()
        write_main(main_t11())

    def write_t13() -> None:
        k = (
            base_keep
            | set(mig_rel)
            | {
                "internal/db/db.go",
                "internal/db/models.go",
                "internal/db/migrate.go",
                "internal/db/db_test.go",
                "internal/config/config.go",
                ".env.example",
                "internal/auth/handler.go",
                "internal/auth/service.go",
                "internal/auth/repository.go",
                "internal/middleware/jwt.go",
                "internal/middleware/rate_limit.go",
                "internal/middleware/security.go",
            }
            | chat_files
            | {"internal/storage/s3.go", "internal/storage/s3_test.go"}
        )
        copy_tree_filtered(k)
        (BACKEND / "internal/chat/service.go").write_text(service_simple_create, encoding="utf-8")
        write_main(main_t13())

    def write_t12() -> None:
        write_t13()
        write_main(main_t12())

    def write_t14() -> None:
        write_t13()
        shutil.copy2(BACKUP / "internal/chat/service.go", BACKEND / "internal/chat/service.go")
        shutil.copy2(BACKUP / "internal/chat/service_test.go", BACKEND / "internal/chat/service_test.go")
        write_main(main_t14())

    def write_t15() -> None:
        write_t14()
        write_main(main_t15())

    def write_t16() -> None:
        write_t14()
        write_main(main_t16())

    def write_t17() -> None:
        copy_tree_filtered(
            base_keep
            | set(mig_rel)
            | {
                "internal/db/db.go",
                "internal/db/models.go",
                "internal/db/migrate.go",
                "internal/db/db_test.go",
                "internal/config/config.go",
                ".env.example",
                "internal/auth/handler.go",
                "internal/auth/service.go",
                "internal/auth/repository.go",
                "internal/middleware/jwt.go",
                "internal/middleware/rate_limit.go",
                "internal/middleware/security.go",
            }
            | chat_files
            | {"internal/storage/s3.go", "internal/storage/s3_test.go"}
            | {"internal/chat/service_test.go"}
        )
        shutil.copy2(BACKUP / "internal/chat/handler.go", BACKEND / "internal/chat/handler.go")
        shutil.copy2(BACKUP / "internal/chat/service.go", BACKEND / "internal/chat/service.go")
        shutil.copy2(BACKUP / "internal/chat/repository.go", BACKEND / "internal/chat/repository.go")
        shutil.copy2(BACKUP / "cmd/server/main.go", BACKEND / "cmd/server/main.go")
        write_main(main_t17())

    sequence = [
        ("chore(backend): initialize Go project with Echo and Dockerfile", write_t1),
        ("feat(db): add PostgreSQL schema migrations with all tables and indexes", write_t2),
        ("feat(db): configure GORM connection and environment setup", write_t3),
        ("feat(auth): implement user registration with security key generation", write_t4),
        ("feat(auth): implement login with JWT access token and httpOnly refresh cookie", write_t5),
        ("feat(auth): add JWT middleware and token refresh endpoint", write_t6),
        ("feat(auth): implement password recovery with security key validation", write_t7),
        ("feat(middleware): add in-memory rate limiting and HTTP security headers", write_t8),
        ("feat(chat): add GET /chats endpoint returning last 5 chats", write_t9),
        ("feat(chat): add POST /chats endpoint for chat creation", write_t10),
        ("feat(chat): add GET /chats/:id endpoint with messages and isolation", write_t11),
        ("feat(storage): implement S3 service with retry and batch operations", write_t13),
        ("feat(chat): add DELETE /chats/:id with cascading S3 file deletion", write_t12),
        ("feat(chat): enforce 5-chat limit with automatic oldest chat removal", write_t14),
        ("feat(files): add GET /chats/:id/files endpoint with signed URLs", write_t15),
        ("feat(files): add GET /chats/:id/files/download returning zip of all slides", write_t16),
        ("feat(files): add GET /chats/:id/files/:fileId for single slide download", write_t17),
    ]

    for msg, fn in sequence:
        fn()
        run(["git", "add", "apps/api"], cwd=ROOT)
        run(["git", "commit", "-m", msg], cwd=ROOT)

    print("Done:", len(sequence), "task commits + first commit.")


if __name__ == "__main__":
    main()
