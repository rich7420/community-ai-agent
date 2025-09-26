#!/bin/bash

# Community AI Agent Backup Script
# This script creates backups of PostgreSQL and MinIO data

set -e

# Configuration
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
POSTGRES_CONTAINER="community-ai-postgres-prod"
MINIO_CONTAINER="community-ai-minio-prod"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}

# Create backup directory
mkdir -p $BACKUP_DIR

echo "Starting backup process at $(date)"

# PostgreSQL Backup
echo "Backing up PostgreSQL database..."
docker exec $POSTGRES_CONTAINER pg_dump -U community_user -d community_ai > $BACKUP_DIR/postgres_backup_$DATE.sql
gzip $BACKUP_DIR/postgres_backup_$DATE.sql
echo "PostgreSQL backup completed: postgres_backup_$DATE.sql.gz"

# MinIO Backup (if container exists)
if docker ps | grep -q $MINIO_CONTAINER; then
    echo "Backing up MinIO data..."
    docker exec $MINIO_CONTAINER tar -czf /tmp/minio_backup_$DATE.tar.gz /data
    docker cp $MINIO_CONTAINER:/tmp/minio_backup_$DATE.tar.gz $BACKUP_DIR/
    echo "MinIO backup completed: minio_backup_$DATE.tar.gz"
else
    echo "MinIO container not running, skipping MinIO backup"
fi

# Cleanup old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup process completed at $(date)"
echo "Backup files:"
ls -la $BACKUP_DIR/
