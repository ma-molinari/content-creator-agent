//go:build integration

package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"content-creator-agent/internal/db"

	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
	"gorm.io/gorm"
)

func TestPostMessage_Multipart_Attachments(t *testing.T) {
	t.Parallel()

	msg := `Create a carousel with these references. ###NO_MARKER###`

	t.Run("happy_path_two_pngs", func(t *testing.T) {
		ts := &trackingStorage{}
		var capt capturedDispatch

		env := newTestEnvWithStorage(t, workerCompletingSlideWithCapture(t, &capt), ts)
		token, userID := registerAndLogin(t, env)
		env.putTestProfile(t, token)
		chatID := createChat(t, env, token)

		png := validPNGBytes(1, 1)
		res, err := postMessageMultipart(t, env, token, chatID, msg, []multipartFile{
			{Filename: "a.png", ContentType: "image/png", Data: png},
			{Filename: "b.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
		})
		require.NoError(t, err)
		defer res.Body.Close()
		require.Equal(t, http.StatusAccepted, res.StatusCode)

		ctx := context.Background()
		var userRows []db.ChatContent
		require.NoError(t, env.DB.WithContext(ctx).Where("chat_id = ? AND role = ?", chatID, db.ChatContentRoleUser).Find(&userRows).Error)
		require.Len(t, userRows, 1)

		var attachments []db.ChatContentAttachment
		require.NoError(t, env.DB.WithContext(ctx).
			Where("chat_content_id = ?", userRows[0].ID).
			Order("sort_order ASC").
			Find(&attachments).Error)
		require.Len(t, attachments, 2)
		for _, a := range attachments {
			require.Equal(t, "image/png", a.MimeType)
			require.Contains(t, a.S3Key, "users/"+userID.String()+"/chat-attachments/")
			require.Positive(t, a.SizeBytes)
		}
		require.EqualValues(t, []int{0, 1}, []int{attachments[0].SortOrder, attachments[1].SortOrder})

		gotKeys := []string{attachments[0].S3Key, attachments[1].S3Key}
		require.Equal(t, gotKeys, capt.lastUserAttachmentKeys())
		ts.mu.Lock()
		for _, key := range gotKeys {
			_, ok := ts.uploads[key]
			require.True(t, ok, "upload missing key %s", key)
			require.Len(t, ts.uploads[key], len(png))
		}
		ts.mu.Unlock()
	})

	t.Run("happy_path_png_over_previous_two_mb_body_limit", func(t *testing.T) {
		ts := &trackingStorage{}
		var capt capturedDispatch

		env := newTestEnvWithStorage(t, workerCompletingSlideWithCapture(t, &capt), ts)
		token, userID := registerAndLogin(t, env)
		env.putTestProfile(t, token)
		chatID := createChat(t, env, token)

		png := append(validPNGBytes(1, 1), make([]byte, 2*1024*1024+128*1024)...)
		res, err := postMessageMultipart(t, env, token, chatID, msg, []multipartFile{
			{Filename: "large-but-valid.png", ContentType: "image/png", Data: png},
		})
		require.NoError(t, err)
		defer res.Body.Close()
		require.Equal(t, http.StatusAccepted, res.StatusCode)

		ctx := context.Background()
		var attachments []db.ChatContentAttachment
		require.NoError(t, env.DB.WithContext(ctx).
			Joins("JOIN chat_content ON chat_content.id = chat_content_attachment.chat_content_id").
			Where("chat_content.chat_id = ?", chatID).
			Find(&attachments).Error)
		require.Len(t, attachments, 1)
		require.Equal(t, "image/png", attachments[0].MimeType)
		require.Contains(t, attachments[0].S3Key, "users/"+userID.String()+"/chat-attachments/")
		require.Equal(t, []string{attachments[0].S3Key}, capt.lastUserAttachmentKeys())
	})

	t.Run("reject_five_attachments", func(t *testing.T) {
		var hits atomic.Int32 // count worker /jobs callbacks
		ts := &trackingStorage{}
		env := newTestEnvWithStorage(t, func(w http.ResponseWriter, _ *http.Request, _ string) {
			hits.Add(1)
			w.WriteHeader(http.StatusOK)
		}, ts)

		token, _ := registerAndLogin(t, env)
		env.putTestProfile(t, token)
		chatID := createChat(t, env, token)
		png := validPNGBytes(1, 1)

		files := make([]multipartFile, 5)
		for i := range files {
			files[i] = multipartFile{Filename: fmt.Sprintf("%d.png", i), ContentType: "image/png", Data: append([]byte(nil), png...)}
		}
		res, err := postMessageMultipart(t, env, token, chatID, msg, files)
		require.NoError(t, err)
		defer res.Body.Close()
		require.Equal(t, http.StatusBadRequest, res.StatusCode)
		b, err := io.ReadAll(res.Body)
		require.NoError(t, err)
		require.True(t, strings.Contains(string(bytes.ToLower(b)), "attachment") ||
			bytes.Contains(bytes.ToLower(b), []byte("max 4")), "body=%q", string(b))

		require.Zero(t, hits.Load())
		ts.mu.Lock()
		require.Len(t, ts.uploads, 0)
		ts.mu.Unlock()

		ctx := context.Background()
		var cnt int64
		require.NoError(t, env.DB.WithContext(ctx).Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&cnt).Error)
		require.Zero(t, cnt)
	})

	t.Run("reject_attachment_over_five_mb", func(t *testing.T) {
		ts := &trackingStorage{}
		var hits atomic.Int32
		env := newTestEnvWithStorage(t, func(w http.ResponseWriter, _ *http.Request, _ string) {
			hits.Add(1)
			w.WriteHeader(http.StatusOK)
		}, ts)
		token, _ := registerAndLogin(t, env)
		env.putTestProfile(t, token)
		chatID := createChat(t, env, token)
		large := make([]byte, 5*1024*1024+1)

		res, err := postMessageMultipart(t, env, token, chatID, msg, []multipartFile{
			{Filename: "a.png", ContentType: "image/png", Data: validPNGBytes(1, 1)},
			{Filename: "blob.bin", ContentType: "image/jpeg", Data: large},
		})
		require.NoError(t, err)
		defer res.Body.Close()
		require.Equal(t, http.StatusRequestEntityTooLarge, res.StatusCode)
		b, err := io.ReadAll(res.Body)
		require.NoError(t, err)
		require.Contains(t, string(b), "5MB")

		require.Zero(t, hits.Load())
		ts.mu.Lock()
		require.Empty(t, ts.uploads)
		ts.mu.Unlock()

		ctx := context.Background()
		var cnt int64
		require.NoError(t, env.DB.WithContext(ctx).Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&cnt).Error)
		require.Zero(t, cnt)
	})

	t.Run("reject_plaintext_when_declared_as_jpeg", func(t *testing.T) {
		ts := &trackingStorage{}
		env := newTestEnvWithStorage(t, noopWorker, ts)
		token, _ := registerAndLogin(t, env)
		env.putTestProfile(t, token)
		chatID := createChat(t, env, token)

		res, err := postMessageMultipart(t, env, token, chatID, msg, []multipartFile{
			{Filename: "x.jpg", ContentType: "image/jpeg", Data: []byte("hello world")},
		})
		require.NoError(t, err)
		defer res.Body.Close()
		require.Equal(t, http.StatusBadRequest, res.StatusCode)
		body, err := io.ReadAll(res.Body)
		require.NoError(t, err)
		require.True(t,
			bytes.Contains(bytes.ToLower(body), []byte("jpeg")) ||
				bytes.Contains(bytes.ToLower(body), []byte("png")),
			"body=%q", string(body))

		ctx := context.Background()
		var cnt int64
		require.NoError(t, env.DB.WithContext(ctx).Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&cnt).Error)
		require.Zero(t, cnt)
	})

	t.Run("upload_failure_no_persist_no_rollbacks_when_all_fail", func(t *testing.T) {
		ts := &trackingStorage{
			failOnUpload: func(string, int) error {
				return fmt.Errorf("s3 down")
			},
		}
		var hits atomic.Int32
		env := newTestEnvWithStorage(t, func(w http.ResponseWriter, _ *http.Request, _ string) {
			hits.Add(1)
			w.WriteHeader(http.StatusOK)
		}, ts)

		token, _ := registerAndLogin(t, env)
		env.putTestProfile(t, token)
		chatID := createChat(t, env, token)
		png := validPNGBytes(1, 1)

		res, err := postMessageMultipart(t, env, token, chatID, msg, []multipartFile{
			{Filename: "a.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
			{Filename: "b.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
		})
		require.NoError(t, err)
		defer res.Body.Close()
		require.Equal(t, http.StatusBadGateway, res.StatusCode)
		b, err := io.ReadAll(res.Body)
		require.NoError(t, err)
		require.Contains(t, string(b), "attachments")

		require.Zero(t, hits.Load())
		ctx := context.Background()
		var jobCnt, contentCnt int64
		require.NoError(t, env.DB.WithContext(ctx).Model(&db.Job{}).Where("chat_id = ?", chatID).Count(&jobCnt).Error)
		require.Zero(t, jobCnt)
		require.NoError(t, env.DB.WithContext(ctx).Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&contentCnt).Error)
		require.Zero(t, contentCnt)

		require.Empty(t, ts.cloneDeleted())
		ts.mu.Lock()
		require.Empty(t, ts.uploads)
		ts.mu.Unlock()
	})

	t.Run("upload_failure_no_persist_partial_cleanup_on_second_failure", func(t *testing.T) {
		ts := &trackingStorage{
			failOnUpload: func(key string, n int) error {
				if n == 1 {
					return fmt.Errorf("s3 down")
				}
				return nil
			},
		}
		var hits atomic.Int32
		env := newTestEnvWithStorage(t, func(w http.ResponseWriter, _ *http.Request, _ string) {
			hits.Add(1)
			w.WriteHeader(http.StatusOK)
		}, ts)

		token, _ := registerAndLogin(t, env)
		env.putTestProfile(t, token)
		chatID := createChat(t, env, token)
		png := validPNGBytes(1, 1)

		res, err := postMessageMultipart(t, env, token, chatID, msg, []multipartFile{
			{Filename: "a.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
			{Filename: "b.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
		})
		require.NoError(t, err)
		defer res.Body.Close()
		require.Equal(t, http.StatusBadGateway, res.StatusCode)
		b, err := io.ReadAll(res.Body)
		require.NoError(t, err)
		require.Contains(t, string(b), "attachments")

		require.Zero(t, hits.Load())

		ctx := context.Background()
		var jobCnt int64
		require.NoError(t, env.DB.WithContext(ctx).Model(&db.Job{}).Where("chat_id = ?", chatID).Count(&jobCnt).Error)
		require.Zero(t, jobCnt)
		var contentCnt int64
		require.NoError(t, env.DB.WithContext(ctx).Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&contentCnt).Error)
		require.Zero(t, contentCnt)

		del := ts.cloneDeleted()
		require.Len(t, del, 1, "cleanup should DeleteMany the first uploaded key")

		ts.mu.Lock()
		require.Len(t, ts.uploads, 1, "successful upload tracked before rollback")
		_, okFirst := ts.uploads[del[0]]
		require.True(t, okFirst)
		ts.mu.Unlock()
	})
}

func TestChatDelete_S3Cleanup_UserAttachments_and_Slides(t *testing.T) {
	t.Parallel()

	msg := `Create a single attached test. ###NO_MARKER###`

	t.Run("delete_explicit_removes_attachment_and_slide_keys", func(t *testing.T) {
		ts := &trackingStorage{}
		env := newTestEnvWithStorage(t, workerCompletingSlideWithCapture(t, &capturedDispatch{}), ts)
		token, _ := registerAndLogin(t, env)
		env.putTestProfile(t, token)
		chatID := createChat(t, env, token)
		png := validPNGBytes(1, 1)

		res, err := postMessageMultipart(t, env, token, chatID, msg, []multipartFile{
			{Filename: "u1.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
			{Filename: "u2.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
		})
		require.NoError(t, err)
		defer res.Body.Close()
		require.Equal(t, http.StatusAccepted, res.StatusCode)

		var jr struct {
			JobID uuid.UUID `json:"jobId"`
		}
		require.NoError(t, json.NewDecoder(res.Body).Decode(&jr))
		status, _ := pollJobDone(t, env, token, chatID, jr.JobID, 5*time.Second)
		require.Equal(t, "done", status)

		ctx := context.Background()
		var attachments []db.ChatContentAttachment
		require.NoError(t, env.DB.WithContext(ctx).
			Joins("JOIN chat_content ON chat_content.id = chat_content_attachment.chat_content_id").
			Where("chat_content.chat_id = ?", chatID).
			Order("chat_content_attachment.sort_order").
			Find(&attachments).Error)
		require.Len(t, attachments, 2)
		wantKeys := []string{attachments[0].S3Key, attachments[1].S3Key, fmt.Sprintf("slides/%s/slide1.jpg", jr.JobID)}

		reqDel, err := http.NewRequest(http.MethodDelete, env.APIURL+"/chats/"+chatID.String(), nil)
		require.NoError(t, err)
		reqDel.Header.Set("Authorization", "Bearer "+token)
		resDel, err := env.HTTPClient.Do(reqDel)
		require.NoError(t, err)
		defer resDel.Body.Close()
		require.Equal(t, http.StatusNoContent, resDel.StatusCode)

		require.ElementsMatch(t, wantKeys, ts.cloneDeleted())

		require.ErrorIs(t,
			env.DB.WithContext(ctx).First(&db.Chat{}, "id = ?", chatID).Error,
			gorm.ErrRecordNotFound,
		)
		var jc, cc, attachCnt, imgCnt int64
		gdb := env.DB.WithContext(ctx)
		require.NoError(t, gdb.Model(&db.Job{}).Where("chat_id = ?", chatID).Count(&jc).Error)
		require.NoError(t, gdb.Model(&db.ChatContent{}).Where("chat_id = ?", chatID).Count(&cc).Error)
		require.NoError(t, gdb.Model(&db.ChatContentAttachment{}).
			Joins("JOIN chat_content ON chat_content.id = chat_content_attachment.chat_content_id").
			Where("chat_content.chat_id = ?", chatID).
			Count(&attachCnt).Error)
		require.NoError(t, gdb.Model(&db.ChatContentImage{}).
			Joins("JOIN chat_content ON chat_content.id = chat_content_image.chat_content_id").
			Where("chat_content.chat_id = ?", chatID).
			Count(&imgCnt).Error)
		require.Zero(t, jc)
		require.Zero(t, cc)
		require.Zero(t, attachCnt)
		require.Zero(t, imgCnt)
	})

	t.Run("evict_oldest_chat_deletes_attachment_and_slide_objects", func(t *testing.T) {
		ts := &trackingStorage{}
		env := newTestEnvWithStorage(t, workerCompletingSlideWithCapture(t, &capturedDispatch{}), ts)
		token, _ := registerAndLogin(t, env)
		env.putTestProfile(t, token)

		png := validPNGBytes(1, 1)

		oldChat := createChat(t, env, token)
		res1, err := postMessageMultipart(t, env, token, oldChat, msg, []multipartFile{
			{Filename: "e1.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
			{Filename: "e2.png", ContentType: "image/png", Data: append([]byte(nil), png...)},
		})
		require.NoError(t, err)
		defer res1.Body.Close()
		require.Equal(t, http.StatusAccepted, res1.StatusCode)
		var jr struct {
			JobID uuid.UUID `json:"jobId"`
		}
		require.NoError(t, json.NewDecoder(res1.Body).Decode(&jr))
		status, _ := pollJobDone(t, env, token, oldChat, jr.JobID, 5*time.Second)
		require.Equal(t, "done", status)

		jobIDForOld := jr.JobID
		wantKeys := snapshotAttachmentAndSlideKeys(t, env, oldChat, jobIDForOld)

		for range 5 {
			createChat(t, env, token)
		}

		ctx := context.Background()
		require.ErrorIs(t,
			env.DB.WithContext(ctx).First(&db.Chat{}, "id = ?", oldChat).Error,
			gorm.ErrRecordNotFound,
		)
		require.ElementsMatch(t, wantKeys, ts.cloneDeleted())
	})
}

func snapshotAttachmentAndSlideKeys(t *testing.T, env *testEnv, chatID, jobID uuid.UUID) []string {
	t.Helper()
	ctx := context.Background()
	var attKeys []string
	require.NoError(t, env.DB.WithContext(ctx).Model(&db.ChatContentAttachment{}).
		Joins("JOIN chat_content ON chat_content.id = chat_content_attachment.chat_content_id").
		Where("chat_content.chat_id = ?", chatID).
		Order("chat_content_attachment.sort_order ASC").
		Pluck("chat_content_attachment.s3_key", &attKeys).Error)
	out := append([]string(nil), attKeys...)
	out = append(out, fmt.Sprintf("slides/%s/slide1.jpg", jobID))
	return out
}
