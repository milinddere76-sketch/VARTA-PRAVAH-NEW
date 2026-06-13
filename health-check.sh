#!/bin/bash

###############################################################################
# VARTAPRAVAH Production Health Check Script
# 
# Purpose: Comprehensive health and readiness verification
# Usage: ./health-check.sh [--full|--quick|--detailed]
# 
# Colors for output
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0
WARNINGS=0

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

###############################################################################
# System Checks
###############################################################################

check_system_resources() {
    print_header "System Resources"
    
    # Check disk space
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -lt 85 ]; then
        print_success "Disk space: ${DISK_USAGE}% used"
    else
        print_warning "Disk space: ${DISK_USAGE}% used (>85%)"
    fi
    
    # Check memory
    MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
    if [ "$MEM_USAGE" -lt 80 ]; then
        print_success "Memory usage: ${MEM_USAGE}%"
    else
        print_warning "Memory usage: ${MEM_USAGE}% (>80%)"
    fi
    
    # Check CPU load
    CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}')
    print_info "CPU load average: $CPU_LOAD"
}

###############################################################################
# Docker Checks
###############################################################################

check_docker() {
    print_header "Docker Status"
    
    # Check Docker daemon
    if docker ps > /dev/null 2>&1; then
        print_success "Docker daemon is running"
    else
        print_error "Docker daemon is not running"
        return
    fi
    
    # Check Docker Compose
    if docker-compose --version > /dev/null 2>&1; then
        print_success "Docker Compose is installed"
    else
        print_error "Docker Compose is not installed"
    fi
    
    # Get Docker version
    DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+')
    print_info "Docker version: $DOCKER_VERSION"
    
    # Check running containers
    CONTAINER_COUNT=$(docker ps --quiet | wc -l)
    if [ "$CONTAINER_COUNT" -ge 7 ]; then
        print_success "All containers running ($CONTAINER_COUNT)"
    else
        print_warning "Expected 7+ containers, found $CONTAINER_COUNT"
    fi
}

###############################################################################
# Service Health Checks
###############################################################################

check_fastapi() {
    print_header "FastAPI Service"
    
    # Health endpoint
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health")
    if [ "$HEALTH_RESPONSE" = "200" ]; then
        print_success "API health endpoint responding: 200 OK"
    else
        print_error "API health endpoint failed: HTTP $HEALTH_RESPONSE"
        return
    fi
    
    # Analytics endpoint
    ANALYTICS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/analytics")
    if [ "$ANALYTICS_RESPONSE" = "200" ]; then
        print_success "Analytics endpoint responding: 200 OK"
    else
        print_error "Analytics endpoint failed: HTTP $ANALYTICS_RESPONSE"
    fi
    
    # API response time
    START_TIME=$(date +%s%N | cut -b1-13)
    curl -s "$API_URL/health" > /dev/null
    END_TIME=$(date +%s%N | cut -b1-13)
    RESPONSE_TIME=$((END_TIME - START_TIME))
    
    if [ "$RESPONSE_TIME" -lt 1000 ]; then
        print_success "API response time: ${RESPONSE_TIME}ms"
    else
        print_warning "API response time: ${RESPONSE_TIME}ms (>1000ms)"
    fi
}

check_frontend() {
    print_header "Frontend Service"
    
    FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL/")
    if [ "$FRONTEND_RESPONSE" = "200" ] || [ "$FRONTEND_RESPONSE" = "304" ]; then
        print_success "Frontend responding: HTTP $FRONTEND_RESPONSE"
    else
        print_error "Frontend failed: HTTP $FRONTEND_RESPONSE"
    fi
}

check_postgres() {
    print_header "PostgreSQL Database"
    
    # Check if running
    if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
        print_success "PostgreSQL is running and accepting connections"
    else
        print_error "PostgreSQL is not responding"
        return
    fi
    
    # Database count
    DB_COUNT=$(docker-compose exec -T postgres psql -U postgres -t -c "SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog');" 2>/dev/null | xargs)
    if [ "$DB_COUNT" -gt 0 ]; then
        print_success "Database schemas found: $DB_COUNT"
    else
        print_warning "No custom database schemas found"
    fi
    
    # Table count
    TABLE_COUNT=$(docker-compose exec -T postgres psql -U postgres -d vartapravah -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
    print_info "Database tables: $TABLE_COUNT"
    
    # Database size
    DB_SIZE=$(docker-compose exec -T postgres psql -U postgres -t -c "SELECT pg_size_pretty(pg_database_size('vartapravah'));" 2>/dev/null | xargs)
    print_info "Database size: $DB_SIZE"
    
    # Active connections
    CONNECTIONS=$(docker-compose exec -T postgres psql -U postgres -t -c "SELECT COUNT(*) FROM pg_stat_activity;" 2>/dev/null | xargs)
    if [ "$CONNECTIONS" -lt 50 ]; then
        print_success "Database connections: $CONNECTIONS (healthy)"
    else
        print_warning "Database connections: $CONNECTIONS (potentially high)"
    fi
}

check_redis() {
    print_header "Redis Cache"
    
    # Ping Redis
    if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        print_success "Redis is running and responding"
    else
        print_error "Redis is not responding"
        return
    fi
    
    # Memory usage
    REDIS_MEM=$(docker-compose exec -T redis redis-cli info memory 2>/dev/null | grep "used_memory_human" | cut -d: -f2)
    if [ -n "$REDIS_MEM" ]; then
        print_info "Redis memory usage: $REDIS_MEM"
    fi
    
    # Key count
    KEY_COUNT=$(docker-compose exec -T redis redis-cli dbsize 2>/dev/null | grep -oP '\d+')
    print_info "Redis keys: $KEY_COUNT"
    
    # Redis version
    REDIS_VERSION=$(docker-compose exec -T redis redis-cli info server 2>/dev/null | grep "redis_version" | cut -d: -f2)
    print_info "Redis version: $REDIS_VERSION"
}

###############################################################################
# File System Checks
###############################################################################

check_filesystem() {
    print_header "File System"
    
    # Check output directory
    if [ -d "./output" ]; then
        print_success "Output directory exists"
        OUTPUT_SIZE=$(du -sh ./output 2>/dev/null | cut -f1)
        print_info "Output directory size: $OUTPUT_SIZE"
    else
        print_error "Output directory not found"
    fi
    
    # Check assets
    if [ -d "./app/assets" ]; then
        print_success "Assets directory exists"
        ASSET_COUNT=$(find ./app/assets -type f | wc -l)
        print_info "Asset files: $ASSET_COUNT"
    else
        print_warning "Assets directory not found"
    fi
    
    # Check static files
    if [ -d "./app/static" ]; then
        print_success "Static directory exists"
    else
        print_warning "Static directory not found"
    fi
}

###############################################################################
# Configuration Checks
###############################################################################

check_configuration() {
    print_header "Configuration"
    
    # Check .env file
    if [ -f ".env" ]; then
        print_success ".env file found"
        
        # Check required variables
        REQUIRED_VARS=(
            "DATABASE_URL"
            "YOUTUBE_RTMP_URL"
            "GROQ_API_KEY"
            "NEWS_API_KEY"
            "REDIS_HOST"
        )
        
        for VAR in "${REQUIRED_VARS[@]}"; do
            if grep -q "^$VAR=" .env; then
                print_success "$VAR is configured"
            else
                print_warning "$VAR is not configured"
            fi
        done
    else
        print_error ".env file not found"
    fi
    
    # Check docker-compose files
    if [ -f "docker-compose-hetzner.yml" ]; then
        print_success "Hetzner compose file found"
    else
        print_error "Hetzner compose file not found"
    fi
    
    if [ -f "docker-compose-oracle.yml" ]; then
        print_success "Oracle compose file found"
    else
        print_error "Oracle compose file not found"
    fi
}

###############################################################################
# Security Checks
###############################################################################

check_security() {
    print_header "Security"
    
    # Check file permissions on .env
    if [ -f ".env" ]; then
        PERMS=$(stat -c '%a' .env 2>/dev/null || stat -f '%A' .env 2>/dev/null)
        if [ "$PERMS" = "600" ] || [ "$PERMS" = "640" ]; then
            print_success ".env file permissions are secure: $PERMS"
        else
            print_warning ".env file permissions: $PERMS (should be 600 or 640)"
        fi
    fi
    
    # Check for exposed API keys in logs
    if docker-compose logs 2>/dev/null | grep -i "api_key\|password" | grep -v "^warning\|^info" > /dev/null; then
        print_warning "Potential sensitive data in logs"
    else
        print_success "No exposed sensitive data in recent logs"
    fi
    
    # Check Docker image vulnerabilities (if trivy installed)
    if command -v trivy &> /dev/null; then
        print_info "Trivy vulnerability scanner available"
    else
        print_info "Trivy not installed (optional vulnerability scanner)"
    fi
}

###############################################################################
# Performance Metrics
###############################################################################

check_performance() {
    print_header "Performance Metrics"
    
    # Container resource usage
    if docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}" > /dev/null 2>&1; then
        print_info "Container memory and CPU:"
        docker stats --no-stream --format "{{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}" | tail -n +2 | head -5 | while read line; do
            echo "    $line"
        done
    fi
    
    # Request latency to API
    AVG_LATENCY=0
    for i in {1..5}; do
        LATENCY=$(curl -s -w "%{time_total}\n" -o /dev/null "$API_URL/health")
        AVG_LATENCY=$(echo "$AVG_LATENCY + $LATENCY" | bc)
    done
    AVG_LATENCY=$(echo "scale=3; $AVG_LATENCY / 5" | bc)
    
    if (( $(echo "$AVG_LATENCY < 0.5" | bc -l) )); then
        print_success "Average API latency: ${AVG_LATENCY}s (good)"
    elif (( $(echo "$AVG_LATENCY < 1.0" | bc -l) )); then
        print_warning "Average API latency: ${AVG_LATENCY}s (acceptable)"
    else
        print_warning "Average API latency: ${AVG_LATENCY}s (slow)"
    fi
}

###############################################################################
# Summary Report
###############################################################################

print_summary() {
    print_header "Health Check Summary"
    
    TOTAL=$((PASSED + FAILED + WARNINGS))
    
    echo "Passed:   $PASSED"
    echo "Failed:   $FAILED"
    echo "Warnings: $WARNINGS"
    echo "Total:    $TOTAL"
    
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        if [ $WARNINGS -eq 0 ]; then
            echo -e "${GREEN}✓ All systems are healthy and ready for production${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ System is operational but has $WARNINGS warnings${NC}"
            return 0
        fi
    else
        echo -e "${RED}✗ System has $FAILED critical failures that need attention${NC}"
        return 1
    fi
}

###############################################################################
# Main Execution
###############################################################################

main() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     VARTAPRAVAH Production Health Check Report        ║${NC}"
    echo -e "${BLUE}║            $(date '+%Y-%m-%d %H:%M:%S')                    ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    
    # Parse command line arguments
    QUICK_MODE=false
    if [ "$1" == "--quick" ]; then
        QUICK_MODE=true
    fi
    
    # Run checks
    check_system_resources
    check_docker
    check_configuration
    check_fastapi
    check_frontend
    check_postgres
    check_redis
    
    if [ "$QUICK_MODE" = false ]; then
        check_filesystem
        check_security
        check_performance
    fi
    
    # Print summary
    print_summary
    EXIT_CODE=$?
    
    return $EXIT_CODE
}

# Run main function
main "$@"
exit $?
