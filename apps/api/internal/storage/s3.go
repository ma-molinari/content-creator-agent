package storage

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"log"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	s3types "github.com/aws/aws-sdk-go-v2/service/s3/types"
)

// StorageService abstracts S3 operations used by the API.
type StorageService interface {
	Upload(ctx context.Context, key string, data []byte) error
	GetSignedURL(ctx context.Context, key string, expiry time.Duration) (string, error)
	GetObject(ctx context.Context, key string) ([]byte, error)
	Delete(ctx context.Context, key string) error
	DeleteMany(ctx context.Context, keys []string) error
}

// S3Service implements StorageService against AWS S3.
type S3Service struct {
	bucket string
	client *s3.Client
	presign *s3.PresignClient
}

// NewS3Service builds an S3-backed storage client. bucket and region must be non-empty.
func NewS3Service(region, bucket, accessKeyID, secretAccessKey string) (*S3Service, error) {
	if region == "" || bucket == "" {
		return nil, fmt.Errorf("storage: AWS_REGION and AWS_S3_BUCKET are required")
	}
	ctx := context.Background()
	var opts []func(*config.LoadOptions) error
	opts = append(opts, config.WithRegion(region))
	if accessKeyID != "" && secretAccessKey != "" {
		opts = append(opts, config.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(accessKeyID, secretAccessKey, ""),
		))
	}
	awscfg, err := config.LoadDefaultConfig(ctx, opts...)
	if err != nil {
		return nil, fmt.Errorf("storage: load AWS config: %w", err)
	}
	cli := s3.NewFromConfig(awscfg)
	return &S3Service{
		bucket:  bucket,
		client:  cli,
		presign: s3.NewPresignClient(cli),
	}, nil
}

const maxUploadAttempts = 3

// Upload stores data at key with exponential backoff (3 attempts).
func (s *S3Service) Upload(ctx context.Context, key string, data []byte) error {
	var lastErr error
	for attempt := 0; attempt < maxUploadAttempts; attempt++ {
		_, err := s.client.PutObject(ctx, &s3.PutObjectInput{
			Bucket: aws.String(s.bucket),
			Key:    aws.String(key),
			Body:   bytes.NewReader(data),
		})
		if err == nil {
			return nil
		}
		lastErr = err
		log.Printf("storage: PutObject attempt %d failed for key %q: %v", attempt+1, key, err)
		if attempt < maxUploadAttempts-1 {
			d := time.Duration(1<<attempt) * 100 * time.Millisecond
			select {
			case <-ctx.Done():
				return fmt.Errorf("storage: upload cancelled: %w", ctx.Err())
			case <-time.After(d):
			}
		}
	}
	return fmt.Errorf("storage: PutObject after %d attempts for key %q: %w", maxUploadAttempts, key, lastErr)
}

// GetSignedURL returns a presigned GET URL for key.
func (s *S3Service) GetSignedURL(ctx context.Context, key string, expiry time.Duration) (string, error) {
	out, err := s.presign.PresignGetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	}, func(o *s3.PresignOptions) {
		o.Expires = expiry
	})
	if err != nil {
		return "", fmt.Errorf("storage: PresignGetObject for key %q: %w", key, err)
	}
	return out.URL, nil
}

// GetObject downloads the object body for key.
func (s *S3Service) GetObject(ctx context.Context, key string) ([]byte, error) {
	out, err := s.client.GetObject(ctx, &s3.GetObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return nil, fmt.Errorf("storage: GetObject for key %q: %w", key, err)
	}
	defer out.Body.Close()
	data, err := io.ReadAll(out.Body)
	if err != nil {
		return nil, fmt.Errorf("storage: read body for key %q: %w", key, err)
	}
	return data, nil
}

// Delete removes a single object.
func (s *S3Service) Delete(ctx context.Context, key string) error {
	_, err := s.client.DeleteObject(ctx, &s3.DeleteObjectInput{
		Bucket: aws.String(s.bucket),
		Key:    aws.String(key),
	})
	if err != nil {
		return fmt.Errorf("storage: DeleteObject for key %q: %w", key, err)
	}
	return nil
}

const deleteBatchSize = 1000

// DeleteMany removes multiple keys using batched DeleteObjects (up to 1000 per call).
func (s *S3Service) DeleteMany(ctx context.Context, keys []string) error {
	if len(keys) == 0 {
		return nil
	}
	for i := 0; i < len(keys); i += deleteBatchSize {
		end := i + deleteBatchSize
		if end > len(keys) {
			end = len(keys)
		}
		batch := keys[i:end]
		objs := make([]s3types.ObjectIdentifier, 0, len(batch))
		for _, k := range batch {
			k := k
			objs = append(objs, s3types.ObjectIdentifier{Key: aws.String(k)})
		}
		out, err := s.client.DeleteObjects(ctx, &s3.DeleteObjectsInput{
			Bucket: aws.String(s.bucket),
			Delete: &s3types.Delete{Objects: objs, Quiet: aws.Bool(true)},
		})
		if err != nil {
			return fmt.Errorf("storage: DeleteObjects batch starting at %d: %w", i, err)
		}
		if len(out.Errors) > 0 {
			e := out.Errors[0]
			return fmt.Errorf("storage: DeleteObjects error for key %s: %s", aws.ToString(e.Key), aws.ToString(e.Message))
		}
	}
	return nil
}
