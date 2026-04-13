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
	// ProfileDataRoot is the server base path; each user has instagram-audits/<user_uuid>/AUDIT.md and BRAND.md.
	ProfileDataRoot string
	// WorkerURL is the base URL of the Python worker (e.g. http://worker:8000).
	WorkerURL string
	// WorkerAPIKey is shared between the Go API and the worker for internal calls.
	WorkerAPIKey string
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
		ProfileDataRoot:    os.Getenv("PROFILE_DATA_ROOT"),
		WorkerURL:          os.Getenv("WORKER_URL"),
		WorkerAPIKey:       os.Getenv("WORKER_API_KEY"),
	}
}
