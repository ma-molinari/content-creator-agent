//go:build integration

package integration

import (
	"context"
	"encoding/xml"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sort"
	"strings"
	"sync"
	"testing"
	"time"

	"content-creator-agent/internal/db"
	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/storage"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

type protocolObject struct {
	Key          string `xml:"Key"`
	LastModified string `xml:"LastModified"`
	Size         int    `xml:"Size"`
}
type protocolList struct {
	XMLName     xml.Name         `xml:"ListBucketResult"`
	XMLNS       string           `xml:"xmlns,attr"`
	IsTruncated bool             `xml:"IsTruncated"`
	NextToken   string           `xml:"NextContinuationToken,omitempty"`
	Contents    []protocolObject `xml:"Contents"`
}
type protocolDelete struct {
	Objects []struct {
		Key string `xml:"Key"`
	} `xml:"Object"`
}
type protocolError struct {
	Key     string `xml:"Key"`
	Code    string `xml:"Code"`
	Message string `xml:"Message"`
}
type protocolDeleteResult struct {
	XMLName xml.Name        `xml:"DeleteResult"`
	XMLNS   string          `xml:"xmlns,attr"`
	Errors  []protocolError `xml:"Error"`
}

type protocolS3 struct {
	mu                     sync.Mutex
	objects                map[string]time.Time
	failKey                string
	failed                 bool
	listCalls, deleteCalls int
}

func (s *protocolS3) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mu.Lock()
	defer s.mu.Unlock()
	w.Header().Set("Content-Type", "application/xml")
	if r.Method == http.MethodGet && r.URL.Query().Get("list-type") == "2" {
		s.listCalls++
		prefix, token := r.URL.Query().Get("prefix"), r.URL.Query().Get("continuation-token")
		keys := make([]string, 0)
		for key := range s.objects {
			if strings.HasPrefix(key, prefix) && key > token {
				keys = append(keys, key)
			}
		}
		sort.Strings(keys)
		result := protocolList{XMLNS: "http://s3.amazonaws.com/doc/2006-03-01/"}
		if len(keys) > 1000 {
			result.IsTruncated = true
			keys = keys[:1000]
			result.NextToken = keys[len(keys)-1]
		}
		for _, key := range keys {
			result.Contents = append(result.Contents, protocolObject{Key: key, LastModified: s.objects[key].UTC().Format("2006-01-02T15:04:05.000Z"), Size: 1})
		}
		_ = xml.NewEncoder(w).Encode(result)
		return
	}
	if r.Method == http.MethodPost && r.URL.Query().Has("delete") {
		s.deleteCalls++
		var input protocolDelete
		if xml.NewDecoder(r.Body).Decode(&input) != nil {
			http.Error(w, "invalid request", http.StatusBadRequest)
			return
		}
		result := protocolDeleteResult{XMLNS: "http://s3.amazonaws.com/doc/2006-03-01/"}
		for _, obj := range input.Objects {
			if obj.Key == s.failKey && !s.failed {
				result.Errors = append(result.Errors, protocolError{Key: obj.Key, Code: "InternalError", Message: "simulated partial failure"})
				s.failed = true
				continue
			}
			delete(s.objects, obj.Key)
		}
		_ = xml.NewEncoder(w).Encode(result)
		return
	}
	http.NotFound(w, r)
}

func TestS3ReconciliationRecoversFromPartialDelete(t *testing.T) {
	env := newTestEnv(t, nil)
	uid, chatID, jobID := uuid.New(), uuid.New(), uuid.New()
	require.NoError(t, env.DB.Create(&db.User{ID: uid, Email: uuid.NewString() + "@test.invalid", PasswordHash: "hash", SecurityKeyHash: "hash"}).Error)
	t.Cleanup(func() { env.DB.Delete(&db.User{}, "id = ?", uid) })
	require.NoError(t, env.DB.Create(&db.Chat{ID: chatID, UserID: uid, PostType: db.PostTypeSingle}).Error)
	old := time.Now().UTC().Add(-48 * time.Hour).Truncate(time.Second)
	recent := time.Now().UTC()
	require.NoError(t, env.DB.Create(&db.Job{ID: jobID, ChatID: chatID, UserID: uid, Status: db.JobStatusFailed, UpdatedAt: old}).Error)
	prefix := fmt.Sprintf("slides/%s/", jobID)
	fake := &protocolS3{objects: map[string]time.Time{}}
	for i := 0; i < 1002; i++ {
		fake.objects[prefix+fmt.Sprintf("object-%04d", i)] = old
	}
	protected := prefix + "object-0900"
	recentKey := prefix + "object-9999"
	fake.objects[recentKey] = recent
	fake.failKey = prefix + "object-1001"
	require.NoError(t, env.DB.Create(&db.UserProfileReference{ID: uuid.New(), UserID: uid, S3Key: protected}).Error)
	server := httptest.NewServer(fake)
	t.Cleanup(server.Close)
	t.Setenv("AWS_ENDPOINT_URL", server.URL)
	t.Setenv("AWS_ENDPOINT_URL_S3", "")
	client, err := storage.NewS3Service("us-east-1", "rehearsal", "local-test", "local-test", storage.S3Options{})
	require.NoError(t, err)
	cutoff := time.Now().UTC().Add(-24 * time.Hour)
	err = jobs.ReconcileArtifacts(context.Background(), env.DB, client, cutoff)
	require.Error(t, err)
	fake.mu.Lock()
	_, stillPresent := fake.objects[fake.failKey]
	fake.mu.Unlock()
	require.True(t, stillPresent)
	require.NoError(t, jobs.ReconcileArtifacts(context.Background(), env.DB, client, cutoff))
	fake.mu.Lock()
	defer fake.mu.Unlock()
	require.Len(t, fake.objects, 2)
	require.Contains(t, fake.objects, protected)
	require.Contains(t, fake.objects, recentKey)
	require.GreaterOrEqual(t, fake.listCalls, 3)
	require.GreaterOrEqual(t, fake.deleteCalls, 3)
}
