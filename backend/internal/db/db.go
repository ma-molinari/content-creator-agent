package db

import (
	"fmt"
	"log"
	"os"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// Connect opens a PostgreSQL connection via GORM. It panics if DATABASE_URL is unset.
func Connect() *gorm.DB {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		panic("DATABASE_URL is required: set it to a PostgreSQL connection string (e.g. postgres://user:pass@host:5432/dbname?sslmode=disable)")
	}
	gdb, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Warn),
	})
	if err != nil {
		log.Fatalf("database connection failed: %v", err)
	}
	sqlDB, err := gdb.DB()
	if err != nil {
		log.Fatalf("database pool: %v", err)
	}
	if err := sqlDB.Ping(); err != nil {
		log.Fatalf("database ping failed: %v", err)
	}
	return gdb
}

// ConnectWithURL is like Connect but uses an explicit DSN (for tests).
func ConnectWithURL(dsn string) (*gorm.DB, error) {
	if dsn == "" {
		return nil, fmt.Errorf("DATABASE_URL is required: set it to a PostgreSQL connection string")
	}
	return gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent),
	})
}
