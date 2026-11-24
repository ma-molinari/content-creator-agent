package main

import (
	"context"
	"flag"
	"log"

	"content-creator-agent/internal/config"
	"content-creator-agent/internal/db"
	"content-creator-agent/internal/profile"
	"content-creator-agent/internal/storage"
)

func main() {
	apply := flag.Bool("apply", false, "remover referências cadastradas e suas origens no S3")
	flag.Parse()
	if !*apply {
		log.Fatal("use -apply após parar as instâncias antigas e aguardar os jobs ativos")
	}
	cfg := config.Load()
	database, err := db.ConnectWithURL(cfg.DatabaseURL)
	if err != nil {
		log.Fatal(err)
	}
	store, err := storage.NewS3Service(cfg.AWSRegion, cfg.S3Bucket, cfg.AWSAccessKeyID, cfg.AWSSecretAccessKey, storage.S3Options{ForcePathStyle: cfg.S3ForcePathStyle, PublicEndpoint: cfg.S3PublicEndpoint})
	if err != nil {
		log.Fatal(err)
	}
	removed, err := profile.RetireReferences(context.Background(), database, store)
	if err != nil {
		log.Fatalf("limpeza interrompida após %d referências: %v", removed, err)
	}
	log.Printf("referências removidas: %d", removed)
}
