#!/bin/bash

# Community AI Agent - Production Deployment Script
# For opensource4you.917420.xyz domain

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_error "Environment file .env not found!"
    print_status "Please create .env file from env.production.example:"
    print_status "cp env.production.example .env"
    print_status "Then edit .env with your API keys"
    exit 1
fi

# Check if SSL certificates exist
if [ ! -f /etc/ssl/certs/opensource4you.917420.xyz.crt ] || [ ! -f /etc/ssl/private/opensource4you.917420.xyz.key ]; then
    print_warning "SSL certificates not found!"
    print_status "Please ensure SSL certificates are installed:"
    print_status "- /etc/ssl/certs/opensource4you.917420.xyz.crt"
    print_status "- /etc/ssl/private/opensource4you.917420.xyz.key"
    print_status ""
    print_status "You can use Let's Encrypt:"
    print_status "sudo certbot certonly --standalone -d opensource4you.917420.xyz"
    print_status ""
    read -p "Continue without SSL? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Stop existing services
print_status "🛑 Stopping existing services..."
if [ -f docker-compose.yml ]; then
    docker-compose down --remove-orphans 2>/dev/null || true
fi
if [ -f docker-compose.debian.yml ]; then
    docker-compose -f docker-compose.debian.yml down --remove-orphans 2>/dev/null || true
fi

# Clean up old containers
print_status "🧹 Cleaning up old containers..."
docker system prune -f

# Create necessary directories
print_status "📁 Creating necessary directories..."
mkdir -p logs/nginx
mkdir -p docker/nginx/ssl

# Copy SSL certificates if they exist
if [ -f /etc/ssl/certs/opensource4you.917420.xyz.crt ] && [ -f /etc/ssl/private/opensource4you.917420.xyz.key ]; then
    print_status "🔒 Copying SSL certificates..."
    sudo cp /etc/ssl/certs/opensource4you.917420.xyz.crt docker/nginx/ssl/
    sudo cp /etc/ssl/private/opensource4you.917420.xyz.key docker/nginx/ssl/
    sudo chown $USER:$USER docker/nginx/ssl/*
fi

# Build and start services
print_status "🔨 Building and starting production services..."
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be ready
print_status "⏳ Waiting for services to be ready..."
print_status "The system will automatically:"
print_status "- Start all services (PostgreSQL, Redis, MinIO, API, Frontend, Nginx)"
print_status "- Wait for dependency services health checks to pass"
print_status "- Automatically initialize data collection (Slack and GitHub data)"
print_status "- Generate embeddings and build FAISS index"
print_status "- Start API services"
sleep 60

# Check service status
print_status "📊 Checking service status..."
docker-compose -f docker-compose.production.yml ps

# Test services
print_status "🧪 Testing services..."

# Test API
if curl -f https://opensource4you.917420.xyz/api/health/ > /dev/null 2>&1; then
    print_success "✅ API is responding"
else
    print_warning "⚠️ API is not responding"
fi

# Test Frontend
if curl -f https://opensource4you.917420.xyz/ > /dev/null 2>&1; then
    print_success "✅ Frontend is responding"
else
    print_warning "⚠️ Frontend is not responding"
fi

# Test MinIO
if curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    print_success "✅ MinIO is responding"
else
    print_warning "⚠️ MinIO is not responding"
fi

# Show deployment information
print_success "🎉 Production deployment completed!"
echo ""
print_status "🌐 Access URLs:"
echo "  Frontend: https://opensource4you.917420.xyz"
echo "  API: https://opensource4you.917420.xyz/api"
echo "  API Docs: https://opensource4you.917420.xyz/api/docs"
echo "  Health Check: https://opensource4you.917420.xyz/health"
echo ""
print_status "🔧 Management Commands:"
echo "  View logs: docker-compose -f docker-compose.production.yml logs -f"
echo "  Stop services: docker-compose -f docker-compose.production.yml down"
echo "  Restart services: docker-compose -f docker-compose.production.yml restart"
echo "  Update services: docker-compose -f docker-compose.production.yml pull && docker-compose -f docker-compose.production.yml up -d"
echo ""
print_status "📚 Production Tips:"
echo "  - Monitor logs: docker-compose -f docker-compose.production.yml logs -f app"
echo "  - Check SSL certificate expiry: sudo certbot certificates"
echo "  - Set up automated backups for PostgreSQL and MinIO"
echo "  - Monitor disk space for logs and data volumes"
echo "  - Set up log rotation for nginx logs"
echo ""
print_status "🔒 Security Notes:"
echo "  - Only ports 80 and 443 are exposed externally"
echo "  - All internal services communicate via Docker network"
echo "  - SSL certificates are required for HTTPS"
echo "  - Rate limiting is enabled for API endpoints"
