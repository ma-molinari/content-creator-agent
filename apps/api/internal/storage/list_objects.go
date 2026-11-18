package storage

import (
	"context"
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

type ObjectInfo struct {
	Key          string
	LastModified *time.Time
}

// ListObjects returns every object under a prefix; missing timestamps must not be treated as old.
func (s *S3Service) ListObjects(ctx context.Context, prefix string) ([]ObjectInfo, error) {
	paginator := s3.NewListObjectsV2Paginator(s.client, &s3.ListObjectsV2Input{Bucket: aws.String(s.bucket), Prefix: aws.String(prefix)})
	var out []ObjectInfo
	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("storage: list objects: %w", err)
		}
		for _, obj := range page.Contents {
			if obj.Key != nil {
				out = append(out, ObjectInfo{Key: *obj.Key, LastModified: obj.LastModified})
			}
		}
	}
	return out, nil
}
