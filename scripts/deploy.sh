#!/bin/bash

# Production deployment script for Ultravox-Twilio Integration Service

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_IMAGE_NAME="ultravox-twilio-service"
DOCKER_TAG="${DOCKER_TAG:-latest}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if environment file exists
    ENV_FILE="$PROJECT_ROOT/.env.$ENVIRONMENT"
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file $ENV_FILE not found"
        log_info "Please create $ENV_FILE with your configuration"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to build Docker image
build_image() {
    log_info "Building Docker image..."
    
    cd "$PROJECT_ROOT"
    
    # Build the production image
    docker build \
        --target production \
        --tag "$DOCKER_IMAGE_NAME:$DOCKER_TAG" \
        --tag "$DOCKER_IMAGE_NAME:latest" \
        .
    
    log_success "Docker image built successfully"
}

# Function to run tests
run_tests() {
    log_info "Running tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run tests in a temporary container
    docker run --rm \
        --env-file ".env.$ENVIRONMENT" \
        -v "$PROJECT_ROOT/tests:/app/tests:ro" \
        "$DOCKER_IMAGE_NAME:$DOCKER_TAG" \
        python -m pytest tests/ -v --tb=short
    
    log_success "Tests passed"
}

# Function to deploy with docker-compose
deploy() {
    log_info "Deploying application..."
    
    cd "$PROJECT_ROOT"
    
    # Load environment variables
    export $(grep -v '^#' ".env.$ENVIRONMENT" | xargs)
    
    # Stop existing containers
    docker-compose down --remove-orphans
    
    # Start new containers
    if [[ "$ENVIRONMENT" == "production" ]]; then
        docker-compose --profile production up -d
    else
        docker-compose up -d
    fi
    
    # Wait for health check
    log_info "Waiting for service to be healthy..."
    sleep 10
    
    # Check if service is running
    if docker-compose ps | grep -q "Up"; then
        log_success "Application deployed successfully"
        
        # Show service status
        docker-compose ps
        
        # Show logs
        log_info "Recent logs:"
        docker-compose logs --tail=20 ultravox-twilio-service
    else
        log_error "Deployment failed - service is not running"
        docker-compose logs ultravox-twilio-service
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --environment, -e    Environment to deploy (default: production)"
    echo "  --tag, -t           Docker image tag (default: latest)"
    echo "  --skip-tests        Skip running tests before deployment"
    echo "  --build-only        Only build the image, don't deploy"
    echo "  --help, -h          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Deploy to production"
    echo "  $0 -e staging               # Deploy to staging"
    echo "  $0 --skip-tests             # Deploy without running tests"
    echo "  $0 --build-only             # Only build the image"
}

# Parse command line arguments
SKIP_TESTS=false
BUILD_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -t|--tag)
            DOCKER_TAG="$2"
            shift 2
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main deployment process
main() {
    log_info "Starting deployment process..."
    log_info "Environment: $ENVIRONMENT"
    log_info "Docker tag: $DOCKER_TAG"
    
    check_prerequisites
    build_image
    
    if [[ "$SKIP_TESTS" == "false" ]]; then
        run_tests
    else
        log_warning "Skipping tests as requested"
    fi
    
    if [[ "$BUILD_ONLY" == "false" ]]; then
        deploy
        log_success "Deployment completed successfully!"
        log_info "Service is available at: http://localhost:8000"
        log_info "API documentation: http://localhost:8000/docs"
    else
        log_success "Build completed successfully!"
    fi
}

# Run main function
main "$@"