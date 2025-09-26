#!/bin/bash

# Community AI Agent Restore Script
# This script restores PostgreSQL and MinIO data from backups

set -e

# Configuration
BACKUP_DIR="/backups"
POSTGRES_CONTAINER="community-ai-postgres-prod"
MINIO_CONTAINER="community-ai-minio-prod"

# Function to show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -d, --date DATE     Restore from backup with specific date (YYYYMMDD_HHMMSS)"
    echo "  -l, --list          List available backups"
    echo "  -h, --help          Show this help message"
    exit 1
}

# Function to list available backups
list_backups() {
    echo "Available PostgreSQL backups:"
    ls -la $BACKUP_DIR/postgres_backup_*.sql.gz 2>/dev/null || echo "No PostgreSQL backups found"
    echo ""
    echo "Available MinIO backups:"
    ls -la $BACKUP_DIR/minio_backup_*.tar.gz 2>/dev/null || echo "No MinIO backups found"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--date)
            BACKUP_DATE="$2"
            shift 2
            ;;
        -l|--list)
            list_backups
            exit 0
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option $1"
            usage
            ;;
    esac
done

# If no date specified, use the latest backup
if [ -z "$BACKUP_DATE" ]; then
    LATEST_POSTGRES=$(ls -t $BACKUP_DIR/postgres_backup_*.sql.gz 2>/dev/null | head -n1)
    if [ -z "$LATEST_POSTGRES" ]; then
        echo "No PostgreSQL backups found"
        exit 1
    fi
    BACKUP_DATE=$(basename $LATEST_POSTGRES | sed 's/postgres_backup_\(.*\)\.sql\.gz/\1/')
    echo "Using latest backup: $BACKUP_DATE"
fi

# Verify backup files exist
POSTGRES_BACKUP="$BACKUP_DIR/postgres_backup_$BACKUP_DATE.sql.gz"
MINIO_BACKUP="$BACKUP_DIR/minio_backup_$BACKUP_DATE.tar.gz"

if [ ! -f "$POSTGRES_BACKUP" ]; then
    echo "PostgreSQL backup not found: $POSTGRES_BACKUP"
    exit 1
fi

echo "Starting restore process at $(date)"
echo "Restoring from backup: $BACKUP_DATE"

# Confirm restore
read -p "This will overwrite existing data. Are you sure? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled"
    exit 1
fi

# PostgreSQL Restore
echo "Restoring PostgreSQL database..."
gunzip -c $POSTGRES_BACKUP | docker exec -i $POSTGRES_CONTAINER psql -U community_user -d community_ai
echo "PostgreSQL restore completed"

# MinIO Restore (if backup exists and container is running)
if [ -f "$MINIO_BACKUP" ] && docker ps | grep -q $MINIO_CONTAINER; then
    echo "Restoring MinIO data..."
    docker cp $MINIO_BACKUP $MINIO_CONTAINER:/tmp/
    docker exec $MINIO_CONTAINER tar -xzf /tmp/minio_backup_$BACKUP_DATE.tar.gz -C /
    echo "MinIO restore completed"
elif [ -f "$MINIO_BACKUP" ]; then
    echo "MinIO backup exists but container is not running. Please start MinIO container first."
else
    echo "No MinIO backup found for date $BACKUP_DATE"
fi

echo "Restore process completed at $(date)"
