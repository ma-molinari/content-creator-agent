package storage

import (
	"context"
	"testing"
)

func TestDeleteManyEmpty(t *testing.T) {
	s := &S3Service{bucket: "b"}
	if err := s.DeleteMany(context.Background(), nil); err != nil {
		t.Fatal(err)
	}
	if err := s.DeleteMany(context.Background(), []string{}); err != nil {
		t.Fatal(err)
	}
}
