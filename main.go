package main

import (
	"context"
	"log"
	"time"

	"your-module/roleChangeAuditTrail"
)

func main() {
	config := &roleChangeAuditTrail.Config{
		APIKey:          "your-api-key",
		OutputFormat:    "json",
		OutputPath:      "role-changes.json",
		LookbackPeriod: 30 * 24 * time.Hour, // 30 days
	}

	tracker, err := roleChangeAuditTrail.NewRoleChangeTracker(config)
	if err != nil {
		log.Fatalf("Failed to create tracker: %v", err)
	}

	changes, err := tracker.TrackRoleChanges(context.Background())
	if err != nil {
		log.Fatalf("Failed to track changes: %v", err)
	}

	if err := tracker.SaveChanges(changes); err != nil {
		log.Fatalf("Failed to save changes: %v", err)
	}
} 