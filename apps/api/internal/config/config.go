package config

import (
	"os"
	"strconv"
	"strings"
)

// Config holds application settings loaded from environment variables.
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
	S3ForcePathStyle   bool
	S3PublicEndpoint   string
	// WorkerURL is the base URL of the Python worker (e.g. http://worker:8000).
	WorkerURL string
	// WorkerAPIKey is shared between the Go API and the worker for internal calls.
	WorkerAPIKey         string
	StructuredWorkerURLs []string
	// StuckJobCron runs stuck-job cleanup (default every 10 minutes UTC). Empty disables the job.
	StuckJobCron string
	// StuckJobProcessingMinutes marks processing jobs as failed when UpdatedAt is older than this (default 20).
	StuckJobProcessingMinutes           int
	ArtifactReconcileEnabled            bool
	StructuredPostsEnabled              bool
	StructuredVisualV2Enabled           bool
	StructuredVisualV2MutationsDisabled bool
	ArtifactReconcileCron               string
	ArtifactReconcileGraceHours         int
	// ProfileRefMaxCount caps optional design reference uploads per user (default 8).
	ProfileRefMaxCount int
	// ProfileRefMaxBytes is the max size per reference image in bytes (default 5MB).
	ProfileRefMaxBytes int64
}

// Load reads configuration from the environment.
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
	var structuredURLs []string
	for _, address := range strings.Split(os.Getenv("STRUCTURED_WORKER_URLS"), ",") {
		if address = strings.TrimSpace(address); address != "" {
			structuredURLs = append(structuredURLs, address)
		}
	}
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	stuckJobCron := os.Getenv("STUCK_JOB_CRON")
	if stuckJobCron == "" {
		stuckJobCron = "*/10 * * * *"
	}
	stuckJobMinutes := 20
	if v := strings.TrimSpace(os.Getenv("STUCK_JOB_PROCESSING_MINUTES")); v != "" {
		if n, err := strconv.Atoi(v); err == nil && n > 0 {
			stuckJobMinutes = n
		}
	}
	artifactCron := strings.TrimSpace(os.Getenv("ARTIFACT_RECONCILE_CRON"))
	if artifactCron == "" {
		artifactCron = "0 4 * * *"
	}
	artifactGraceHours := 24
	if n, err := strconv.Atoi(strings.TrimSpace(os.Getenv("ARTIFACT_RECONCILE_GRACE_HOURS"))); err == nil && n >= 24 {
		artifactGraceHours = n
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
		Port:                                port,
		DatabaseURL:                         os.Getenv("DATABASE_URL"),
		JWTSecret:                           os.Getenv("JWT_SECRET"),
		JWTRefreshSecret:                    os.Getenv("JWT_REFRESH_SECRET"),
		CORSAllowedOrigins:                  allowed,
		AWSRegion:                           os.Getenv("AWS_REGION"),
		AWSAccessKeyID:                      os.Getenv("AWS_ACCESS_KEY_ID"),
		AWSSecretAccessKey:                  os.Getenv("AWS_SECRET_ACCESS_KEY"),
		S3Bucket:                            os.Getenv("AWS_S3_BUCKET"),
		S3ForcePathStyle:                    strings.EqualFold(strings.TrimSpace(os.Getenv("AWS_S3_FORCE_PATH_STYLE")), "true"),
		S3PublicEndpoint:                    strings.TrimSpace(os.Getenv("AWS_S3_PUBLIC_ENDPOINT")),
		WorkerURL:                           os.Getenv("WORKER_URL"),
		WorkerAPIKey:                        os.Getenv("WORKER_API_KEY"),
		StructuredWorkerURLs:                structuredURLs,
		StuckJobCron:                        stuckJobCron,
		StuckJobProcessingMinutes:           stuckJobMinutes,
		StructuredPostsEnabled:              strings.EqualFold(strings.TrimSpace(os.Getenv("STRUCTURED_POSTS_ENABLED")), "true"),
		StructuredVisualV2Enabled:           strings.EqualFold(strings.TrimSpace(os.Getenv("STRUCTURED_VISUAL_V2_ENABLED")), "true"),
		StructuredVisualV2MutationsDisabled: strings.EqualFold(strings.TrimSpace(os.Getenv("STRUCTURED_VISUAL_V2_MUTATIONS_DISABLED")), "true"),
		ArtifactReconcileEnabled:            strings.EqualFold(strings.TrimSpace(os.Getenv("ARTIFACT_RECONCILE_ENABLED")), "true"),
		ArtifactReconcileCron:               artifactCron,
		ArtifactReconcileGraceHours:         artifactGraceHours,
		ProfileRefMaxCount:                  profileRefMax,
		ProfileRefMaxBytes:                  profileRefMaxBytes,
	}
}
