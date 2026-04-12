package config

import (
	"os"
	"strings"
)

// Load reads configuration from the environment.
type Config struct {
	Port               string
	DatabaseURL        string
	JWTSecret          string
	JWTRefreshSecret   string
	CORSAllowedOrigins []string
	AWSRegion          string
	AWSAccessKeyID     string
	AWSSecretAccessKey string
	S3Bucket           string
	OpenAIAPIKey       string
	OpenAIModel        string
	// ProfileDataRoot is the server base path; each user has instagram-audits/<user_uuid>/AUDIT.md and BRAND.md.
	ProfileDataRoot string
	// RepoRoot is the repository root (contains scripts/export-slides.js).
	RepoRoot string
	// ExportTimeout is the maximum time allowed for one Playwright export run.
	ExportTimeout string
}

func Load() Config {
	origins := os.Getenv("CORS_ALLOWED_ORIGINS")
	var allowed []string
	if origins != "" {
		for _, o := range strings.Split(origins, ",") {
			o = strings.TrimSpace(o)
			if o != "" {
				allowed = append(allowed, o)
			}
		}
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	openAIModel := os.Getenv("OPENAI_MODEL")
	if openAIModel == "" {
		openAIModel = "gpt-5.4-mini"
	}
	return Config{
		Port:               port,
		DatabaseURL:        os.Getenv("DATABASE_URL"),
		JWTSecret:          os.Getenv("JWT_SECRET"),
		JWTRefreshSecret:   os.Getenv("JWT_REFRESH_SECRET"),
		CORSAllowedOrigins: allowed,
		AWSRegion:          os.Getenv("AWS_REGION"),
		AWSAccessKeyID:     os.Getenv("AWS_ACCESS_KEY_ID"),
		AWSSecretAccessKey: os.Getenv("AWS_SECRET_ACCESS_KEY"),
		S3Bucket:           os.Getenv("AWS_S3_BUCKET"),
		OpenAIAPIKey:       os.Getenv("OPENAI_API_KEY"),
		OpenAIModel:        openAIModel,
		ProfileDataRoot:    os.Getenv("PROFILE_DATA_ROOT"),
		RepoRoot:           os.Getenv("REPO_ROOT"),
		ExportTimeout:      os.Getenv("EXPORT_TIMEOUT"),
	}
}
