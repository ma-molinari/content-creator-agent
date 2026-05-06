//go:build integration

package integration

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/textproto"
	"sync"
	"testing"
	"time"

	"content-creator-agent/internal/jobs"
	"content-creator-agent/internal/storage"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

// png1x1 is a decode-once minimal valid PNG (1×1) so net/http sniff returns image/png.
var png1x1 = func() []byte {
	b, err := base64.StdEncoding.DecodeString("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
	if err != nil {
		panic(err)
	}
	return b
}()

func validPNGBytes(width, height int) []byte {
	if width == 1 && height == 1 {
		out := make([]byte, len(png1x1))
		copy(out, png1x1)
		return out
	}
	panic("integration helper: validPNGBytes only supports 1x1 in this repo")
}

type multipartFile struct {
	Filename    string
	ContentType string
	Data        []byte
}

func postMessageMultipart(t *testing.T, env *testEnv, token string, chatID uuid.UUID, content string, files []multipartFile) (*http.Response, error) {
	t.Helper()
	var buf bytes.Buffer
	mp := multipart.NewWriter(&buf)
	require.NoError(t, mp.WriteField("content", content))
	for _, f := range files {
		hdr := textproto.MIMEHeader{}
		if f.Filename != "" {
			hdr.Set("Content-Disposition",
				fmt.Sprintf(`form-data; name="attachments"; filename="%s"`, f.Filename))
		} else {
			hdr.Set("Content-Disposition", `form-data; name="attachments"`)
		}
		hdr.Set("Content-Type", f.ContentType)
		partW, err := mp.CreatePart(hdr)
		require.NoError(t, err)
		_, err = partW.Write(f.Data)
		require.NoError(t, err)
	}
	require.NoError(t, mp.Close())

	reqURL := fmt.Sprintf("%s/chats/%s/messages", env.APIURL, chatID.String())
	req, err := http.NewRequest(http.MethodPost, reqURL, &buf)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", mp.FormDataContentType())
	req.Header.Set("Authorization", "Bearer "+token)
	return env.HTTPClient.Do(req)
}

func newTestEnvWithStorage(t *testing.T, workerHandler func(w http.ResponseWriter, r *http.Request, apiBase string), stor storage.StorageService) *testEnv {
	t.Helper()
	return newTestEnvCore(t, workerHandler, nil, stor)
}

type capturedDispatch struct {
	mu   sync.Mutex
	last jobs.DispatchPayload
}

func (c *capturedDispatch) setLast(p jobs.DispatchPayload) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.last = p
}

func (c *capturedDispatch) lastUserAttachmentKeys() []string {
	c.mu.Lock()
	defer c.mu.Unlock()
	return append([]string(nil), c.last.UserAttachmentS3Keys...)
}

// trackingStorage records uploads and delete calls while delegating untouched methods to mockStorage.
// Upload runs under a mutex so failOnUpload ordinal n is deterministic (tests do not rely on errgroup scheduling).
type trackingStorage struct {
	mockStorage

	mu sync.Mutex

	uploads       map[string][]byte
	deleted       []string
	failOnUpload  func(key string, n int) error
	uploadOrdinal int
}

var _ storage.StorageService = (*trackingStorage)(nil)

func (ts *trackingStorage) Upload(ctx context.Context, key string, data []byte) error {
	ts.mu.Lock()
	n := ts.uploadOrdinal
	ts.uploadOrdinal++
	hook := ts.failOnUpload
	ts.mu.Unlock()

	if hook != nil {
		if err := hook(key, n); err != nil {
			return err
		}
	}

	ts.mu.Lock()
	defer ts.mu.Unlock()
	if ts.uploads == nil {
		ts.uploads = make(map[string][]byte)
	}
	ts.uploads[key] = append([]byte(nil), data...)
	return nil
}

func (ts *trackingStorage) Delete(ctx context.Context, key string) error {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	ts.deleted = append(ts.deleted, key)
	return nil
}

func (ts *trackingStorage) DeleteMany(ctx context.Context, keys []string) error {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	ts.deleted = append(ts.deleted, keys...)
	return nil
}

func (ts *trackingStorage) cloneDeleted() []string {
	ts.mu.Lock()
	defer ts.mu.Unlock()
	return append([]string(nil), ts.deleted...)
}

func workerCompletingSlideWithCapture(t *testing.T, capt *capturedDispatch) func(http.ResponseWriter, *http.Request, string) {
	return func(w http.ResponseWriter, r *http.Request, apiBase string) {
		var p jobs.DispatchPayload
		if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
			t.Errorf("decode dispatch payload: %v", err)
			http.Error(w, "bad request", http.StatusBadRequest)
			return
		}
		capt.setLast(p)
		jobID := p.JobID
		go func() {
			cb := map[string]any{
				"assistantText": "Integration assistant reply",
				"artifacts": []map[string]any{
					{"s3Key": "slides/" + jobID.String() + "/slide1.jpg", "slideNumber": 1},
				},
			}
			b, err := json.Marshal(cb)
			if err != nil {
				t.Logf("marshal callback: %v", err)
				return
			}
			req, err := http.NewRequest(http.MethodPost, apiBase+"/internal/jobs/"+jobID.String()+"/complete", bytes.NewReader(b))
			if err != nil {
				t.Logf("new callback request: %v", err)
				return
			}
			req.Header.Set("Content-Type", "application/json")
			req.Header.Set("X-Worker-API-Key", IntegrationWorkerAPIKey)
			cli := &http.Client{Timeout: 10 * time.Second}
			resp, err := cli.Do(req)
			if err != nil {
				t.Logf("callback request: %v", err)
				return
			}
			if resp != nil {
				_, _ = io.Copy(io.Discard, resp.Body)
				_ = resp.Body.Close()
			}
		}()
		w.WriteHeader(http.StatusAccepted)
	}
}
