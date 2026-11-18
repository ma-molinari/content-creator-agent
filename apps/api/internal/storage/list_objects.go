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

// WalkObjectPages visits bounded pages; missing timestamps must not be treated as old.
func (s *S3Service) WalkObjectPages(ctx context.Context, prefix string, visit func([]ObjectInfo) error) error {
	paginator := s3.NewListObjectsV2Paginator(s.client, &s3.ListObjectsV2Input{Bucket: aws.String(s.bucket), Prefix: aws.String(prefix)})
	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return fmt.Errorf("storage: list objects: %w", err)
		}
		objects := make([]ObjectInfo, 0, len(page.Contents))
		for _, obj := range page.Contents {
			if obj.Key != nil {
				objects = append(objects, ObjectInfo{Key: *obj.Key, LastModified: obj.LastModified})
			}
		}
		if err := visit(objects); err != nil {
			return err
		}
	}
	return nil
}
