# Build API binary
FROM golang:1.25-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /server ./cmd/server

# Runtime: minimal image with TLS roots for HTTPS to S3 and worker
FROM alpine:3.19
RUN apk add --no-cache ca-certificates wget \
    && addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY --from=builder /server /app/server
RUN chown app:app /app/server
USER app
EXPOSE 8080
ENV PORT=8080
CMD ["/app/server"]
