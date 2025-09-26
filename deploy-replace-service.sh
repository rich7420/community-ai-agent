#!/bin/bash

# Community AI Agent - Replace Existing Service Deployment Script
# For Debian servers with existing nginx configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="opensource4you.917420.xyz"
NGINX_CONFIG="/etc/nginx/sites-available/${DOMAIN}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${DOMAIN}"
SERVICE_NAME="community-ai-agent"

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

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root. Please run as a regular user with sudo privileges."
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if nginx is installed
    if ! command -v nginx &> /dev/null; then
        print_error "Nginx is not installed. Please install Nginx first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Please create it from env.example first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to stop existing services
stop_existing_services() {
    print_status "Stopping existing services..."
    
    # Stop nginx
    sudo systemctl stop nginx 2>/dev/null || print_warning "Nginx was not running"
    
    # Stop any existing Docker containers
    docker-compose -f docker-compose.debian.yml down 2>/dev/null || print_warning "No existing containers to stop"
    
    print_success "Existing services stopped"
}

# Function to backup existing nginx configuration
backup_nginx_config() {
    print_status "Backing up existing nginx configuration..."
    
    if [ -f "$NGINX_CONFIG" ]; then
        sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
        print_success "Existing nginx configuration backed up"
    else
        print_warning "No existing nginx configuration found"
    fi
}

# Function to create nginx configuration
create_nginx_config() {
    print_status "Creating nginx configuration for $DOMAIN..."
    
    sudo tee "$NGINX_CONFIG" > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;
    
    # SSL certificate configuration (update paths as needed)
    ssl_certificate /etc/ssl/certs/$DOMAIN.crt;
    ssl_certificate_key /etc/ssl/private/$DOMAIN.key;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Frontend proxy
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeout for AI responses
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Static files caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        proxy_pass http://localhost:3000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    
    print_success "Nginx configuration created"
}

# Function to enable nginx configuration
enable_nginx_config() {
    print_status "Enabling nginx configuration..."
    
    # Enable new site
    sudo ln -sf "$NGINX_CONFIG" "$NGINX_ENABLED"
    
    # Disable default site if it exists
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    if sudo nginx -t; then
        print_success "Nginx configuration is valid"
    else
        print_error "Nginx configuration test failed"
        exit 1
    fi
    
    print_success "Nginx configuration enabled"
}

# Function to deploy application
deploy_application() {
    print_status "Deploying Community AI Agent application..."
    
    # Build and start containers
    docker-compose -f docker-compose.debian.yml up -d --build
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check if containers are running
    if docker-compose -f docker-compose.debian.yml ps | grep -q "Up"; then
        print_success "Application deployed successfully"
    else
        print_error "Application deployment failed"
        docker-compose -f docker-compose.debian.yml logs
        exit 1
    fi
}

# Function to start nginx
start_nginx() {
    print_status "Starting nginx..."
    
    sudo systemctl start nginx
    sudo systemctl enable nginx
    
    if sudo systemctl is-active --quiet nginx; then
        print_success "Nginx started successfully"
    else
        print_error "Failed to start nginx"
        exit 1
    fi
}

# Function to create systemd service
create_systemd_service() {
    print_status "Creating systemd service..."
    
    sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Community AI Agent
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker-compose -f docker-compose.debian.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.debian.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME.service
    
    print_success "Systemd service created and enabled"
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    # Check if containers are running
    if docker-compose -f docker-compose.debian.yml ps | grep -q "Up"; then
        print_success "Containers are running"
    else
        print_error "Containers are not running"
        return 1
    fi
    
    # Check if nginx is running
    if sudo systemctl is-active --quiet nginx; then
        print_success "Nginx is running"
    else
        print_error "Nginx is not running"
        return 1
    fi
    
    # Test health endpoint
    if curl -s -k "https://$DOMAIN/health" > /dev/null; then
        print_success "Health check passed"
    else
        print_warning "Health check failed (this might be normal if SSL is not configured yet)"
    fi
    
    print_success "Deployment verification completed"
}

# Function to show deployment summary
show_summary() {
    echo ""
    echo "=========================================="
    echo "🚀 Deployment Summary"
    echo "=========================================="
    echo "Domain: https://$DOMAIN"
    echo "API Documentation: https://$DOMAIN/api/docs"
    echo "Health Check: https://$DOMAIN/health"
    echo ""
    echo "Services:"
    echo "- Nginx: $(sudo systemctl is-active nginx)"
    echo "- Community AI Agent: $(sudo systemctl is-active $SERVICE_NAME)"
    echo ""
    echo "Containers:"
    docker-compose -f docker-compose.debian.yml ps
    echo ""
    echo "Next steps:"
    echo "1. Update SSL certificate paths in $NGINX_CONFIG if needed"
    echo "2. Test the application at https://$DOMAIN"
    echo "3. Monitor logs: docker-compose -f docker-compose.debian.yml logs -f"
    echo "=========================================="
}

# Main deployment function
main() {
    echo "🚀 Community AI Agent - Replace Service Deployment"
    echo "Domain: $DOMAIN"
    echo ""
    
    check_root
    check_prerequisites
    stop_existing_services
    backup_nginx_config
    create_nginx_config
    enable_nginx_config
    deploy_application
    start_nginx
    create_systemd_service
    verify_deployment
    show_summary
    
    print_success "🎉 Deployment completed successfully!"
    print_warning "⚠️  Please update SSL certificate paths in $NGINX_CONFIG if needed"
}

# Run main function
main "$@"
