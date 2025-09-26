#!/bin/bash

# Community AI Agent Maintenance Script
# This script handles routine maintenance tasks

set -e

# Configuration
MAINTENANCE_LOG="/tmp/community-ai-logs/maintenance.log"
BACKUP_DIR="/backups"
LOG_RETENTION_DAYS=30
CLEANUP_THRESHOLD=80  # Disk usage percentage threshold

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
    echo "$(date): [INFO] $1" >> $MAINTENANCE_LOG
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    echo "$(date): [WARN] $1" >> $MAINTENANCE_LOG
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    echo "$(date): [ERROR] $1" >> $MAINTENANCE_LOG
}

# Create maintenance log directory
mkdir -p $(dirname $MAINTENANCE_LOG)

# Function to check disk usage
check_disk_usage() {
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $usage -gt $CLEANUP_THRESHOLD ]; then
        log_warn "Disk usage is at ${usage}%, above threshold of ${CLEANUP_THRESHOLD}%"
        return 1
    else
        log_info "Disk usage is at ${usage}%, within acceptable limits"
        return 0
    fi
}

# Function to clean up old logs
cleanup_logs() {
    log_info "Starting log cleanup..."
    
    # Clean up application logs older than retention period
    find /var/log/community-ai -name "*.log" -mtime +$LOG_RETENTION_DAYS -delete 2>/dev/null || true
    
    # Clean up Docker logs
    docker system prune -f --volumes
    
    # Clean up old backup files
    find $BACKUP_DIR -name "*.gz" -mtime +30 -delete 2>/dev/null || true
    
    log_info "Log cleanup completed"
}

# Function to update application
update_application() {
    log_info "Starting application update..."
    
    # Pull latest changes
    git pull origin main
    
    # Rebuild and restart services
    docker-compose -f docker-compose.prod.yml build
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services to be ready
    sleep 30
    
    # Health check
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "Application update completed successfully"
    else
        log_error "Application update failed - health check failed"
        return 1
    fi
}

# Function to backup data
backup_data() {
    log_info "Starting data backup..."
    
    if [ -f "./scripts/backup.sh" ]; then
        ./scripts/backup.sh
        log_info "Data backup completed"
    else
        log_error "Backup script not found"
        return 1
    fi
}

# Function to check service health
check_service_health() {
    log_info "Checking service health..."
    
    # Check if all services are running
    if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_error "Some services are not running"
        return 1
    fi
    
    # Check application health endpoint
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_error "Application health check failed"
        return 1
    fi
    
    log_info "All services are healthy"
}

# Function to restart services
restart_services() {
    log_info "Restarting services..."
    
    docker-compose -f docker-compose.prod.yml restart
    
    # Wait for services to be ready
    sleep 30
    
    # Health check
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_info "Services restarted successfully"
    else
        log_error "Service restart failed - health check failed"
        return 1
    fi
}

# Function to show maintenance status
show_status() {
    log_info "Maintenance Status Report"
    echo "=========================="
    
    # Service status
    echo "Service Status:"
    docker-compose -f docker-compose.prod.yml ps
    
    # Disk usage
    echo -e "\nDisk Usage:"
    df -h
    
    # Memory usage
    echo -e "\nMemory Usage:"
    vm_stat | head -4
    
    # Recent logs
    echo -e "\nRecent Maintenance Logs:"
    tail -20 $MAINTENANCE_LOG 2>/dev/null || echo "No maintenance logs found"
}

# Main maintenance routine
main() {
    local action=${1:-routine}
    
    case $action in
        "routine")
            log_info "Starting routine maintenance..."
            check_disk_usage || cleanup_logs
            check_service_health || restart_services
            log_info "Routine maintenance completed"
            ;;
        "cleanup")
            log_info "Starting cleanup maintenance..."
            cleanup_logs
            log_info "Cleanup maintenance completed"
            ;;
        "update")
            log_info "Starting update maintenance..."
            backup_data
            update_application
            log_info "Update maintenance completed"
            ;;
        "backup")
            log_info "Starting backup maintenance..."
            backup_data
            log_info "Backup maintenance completed"
            ;;
        "restart")
            log_info "Starting restart maintenance..."
            restart_services
            log_info "Restart maintenance completed"
            ;;
        "status")
            show_status
            ;;
        *)
            echo "Usage: $0 [routine|cleanup|update|backup|restart|status]"
            echo ""
            echo "Commands:"
            echo "  routine  - Run routine maintenance (default)"
            echo "  cleanup  - Clean up old logs and files"
            echo "  update   - Update application to latest version"
            echo "  backup   - Create data backup"
            echo "  restart  - Restart all services"
            echo "  status   - Show maintenance status"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
