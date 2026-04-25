package config

import (
	"os"
	"strconv"
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
	// WorkerURL is the base URL of the Python worker (e.g. http://worker:8000).
	WorkerURL string
	// WorkerAPIKey is shared between the Go API and the worker for internal calls.
	WorkerAPIKey string
	// OpenAIAPIKey enables nightly chat summarization when set (see summarizer package).
	OpenAIAPIKey string
	// SummarizeCron is a standard cron expression in UTC (default 02:00 daily).
	SummarizeCron string
	// ProfileRefMaxCount caps optional design reference uploads per user (default 8).
	ProfileRefMaxCount int
	// ProfileRefMaxBytes is the max size per reference image in bytes (default 5MB).
	ProfileRefMaxBytes int64
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
	summarizeCron := os.Getenv("SUMMARIZE_CRON")
	if summarizeCron == "" {
		summarizeCron = "0 2 * * *"
	}
	profileRefMax := 8
	if v := strings.TrimSpace(os.Getenv("PROFILE_REF_MAX_COUNT")); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			profileRefMax = n
		}
	}
	profileRefMaxBytes := int64(5 * 1024 * 1024)
	if v := strings.TrimSpace(os.Getenv("PROFILE_REF_MAX_BYTES")); v != "" {
		if n, err := strconv.ParseInt(v, 10, 64); err == nil && n > 0 {
			profileRefMaxBytes = n
		}
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
		WorkerURL:          os.Getenv("WORKER_URL"),
		WorkerAPIKey:       os.Getenv("WORKER_API_KEY"),
		OpenAIAPIKey:       os.Getenv("OPENAI_API_KEY"),
		SummarizeCron:      summarizeCron,
		ProfileRefMaxCount: profileRefMax,
		ProfileRefMaxBytes: profileRefMaxBytes,
	}
}
