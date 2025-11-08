#!/bin/bash
# ETL Pipeline Runner Script
# Automates the complete ETL pipeline execution from start to finish

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
ENV_FILE=".env"
DOCKER_COMPOSE_FILE="docker-compose.yml"
DB_SERVICE="pgvector"
ETL_SERVICE="etl_pipeline"
MAX_WAIT_TIME=60  # Maximum seconds to wait for database

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose (new format: docker compose)
    if ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose is available"
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    print_success "Docker daemon is running"
    
    # Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file not found. Creating from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Please edit .env file and add your OPENAI_API_KEY"
            print_warning "Press Enter to continue after adding your API key, or Ctrl+C to exit..."
            read -r
        else
            print_error ".env file not found and .env.example doesn't exist."
            exit 1
        fi
    fi
    
    # Check if OPENAI_API_KEY is set
    if grep -q "OPENAI_API_KEY=$" "$ENV_FILE" || ! grep -q "OPENAI_API_KEY=" "$ENV_FILE"; then
        print_warning "OPENAI_API_KEY is not set in .env file"
        print_warning "Please add your OpenAI API key to .env file"
        print_warning "Press Enter to continue anyway, or Ctrl+C to exit..."
        read -r
    else
        print_success ".env file exists and OPENAI_API_KEY is set"
    fi
    
    # Check data directory
    if [ ! -d "data" ]; then
        print_warning "data/ directory not found. Creating it..."
        mkdir -p data/system_design data/standards
        print_warning "Please add your markdown files to data/ directory"
    else
        # Count markdown files
        MD_COUNT=$(find data -name "*.md" -type f 2>/dev/null | wc -l)
        if [ "$MD_COUNT" -eq 0 ]; then
            print_warning "No markdown files found in data/ directory"
        else
            print_success "Found $MD_COUNT markdown file(s) in data/ directory"
        fi
    fi
    
    # Create logs directory
    mkdir -p logs
    print_success "Logs directory ready"
    
    echo ""
}

# Start database
start_database() {
    print_header "Starting Database"
    
    # Check if database is already running
    if docker compose ps "$DB_SERVICE" 2>/dev/null | grep -q "Up"; then
        print_info "Database is already running"
        return 0
    fi
    
    print_info "Starting PostgreSQL with pgvector..."
    docker compose up -d "$DB_SERVICE"
    
    # Wait for database to be healthy
    print_info "Waiting for database to be ready (max ${MAX_WAIT_TIME}s)..."
    local count=0
    while [ $count -lt $MAX_WAIT_TIME ]; do
        if docker compose exec -T "$DB_SERVICE" pg_isready -U postgres >/dev/null 2>&1; then
            print_success "Database is ready!"
            return 0
        fi
        sleep 2
        count=$((count + 2))
        echo -n "."
    done
    echo ""
    
    if [ $count -ge $MAX_WAIT_TIME ]; then
        print_error "Database failed to start within ${MAX_WAIT_TIME} seconds"
        print_info "Checking database logs..."
        docker compose logs --tail=20 "$DB_SERVICE"
        exit 1
    fi
}

# Build ETL pipeline image
build_etl_image() {
    print_header "Building ETL Pipeline Image"
    
    print_info "Building Docker image for ETL pipeline..."
    if docker compose build "$ETL_SERVICE"; then
        print_success "ETL pipeline image built successfully"
    else
        print_error "Failed to build ETL pipeline image"
        exit 1
    fi
    echo ""
}

# Run ETL pipeline
run_etl_pipeline() {
    print_header "Running ETL Pipeline"
    
    # Get environment from command line or use default
    ETL_ENV="${1:-local}"
    print_info "Using environment: $ETL_ENV"
    
    # Export ETL_ENV for docker-compose
    export ETL_ENV="$ETL_ENV"
    
    print_info "Starting ETL pipeline..."
    echo ""
    
    # Run the pipeline and capture exit code
    if docker compose run --rm "$ETL_SERVICE" python -m etl_pipeline.main --env "$ETL_ENV"; then
        echo ""
        print_success "ETL pipeline completed successfully!"
        return 0
    else
        echo ""
        print_error "ETL pipeline failed!"
        return 1
    fi
}

# Show results
show_results() {
    print_header "Pipeline Results"
    
    # Check database connection and count chunks
    print_info "Checking database for loaded chunks..."
    
    if docker compose exec -T "$DB_SERVICE" psql -U postgres -d vector_db -t -c "SELECT COUNT(*) FROM document_chunks;" 2>/dev/null | grep -q "[0-9]"; then
        CHUNK_COUNT=$(docker compose exec -T "$DB_SERVICE" psql -U postgres -d vector_db -t -c "SELECT COUNT(*) FROM document_chunks;" 2>/dev/null | tr -d ' ')
        print_success "Loaded $CHUNK_COUNT chunk(s) into vector database"
    else
        print_warning "Could not retrieve chunk count from database"
    fi
    
    # Show recent logs
    echo ""
    print_info "Recent pipeline logs:"
    docker compose logs --tail=20 "$ETL_SERVICE" 2>/dev/null || print_warning "No logs available"
    
    echo ""
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo ""
        print_error "Pipeline execution failed with exit code $exit_code"
        print_info "Check logs with: docker compose logs $ETL_SERVICE"
    fi
    exit $exit_code
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Main execution
main() {
    print_header "ETL Pipeline Automation Script"
    echo ""
    
    # Parse command line arguments
    ETL_ENV="local"
    SKIP_BUILD=false
    SKIP_DB=false
    DRY_RUN=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --env)
                ETL_ENV="$2"
                shift 2
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-db)
                SKIP_DB=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --env ENV          Environment to use (local, prod, staging) [default: local]"
                echo "  --skip-build       Skip building Docker image"
                echo "  --skip-db          Skip starting database (assume it's already running)"
                echo "  --dry-run          Run pipeline in dry-run mode (test without loading)"
                echo "  --help, -h         Show this help message"
                echo ""
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Run steps
    check_prerequisites
    
    if [ "$SKIP_DB" = false ]; then
        start_database
    else
        print_info "Skipping database start (--skip-db flag set)"
    fi
    
    if [ "$SKIP_BUILD" = false ]; then
        build_etl_image
    else
        print_info "Skipping image build (--skip-build flag set)"
    fi
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Running in DRY-RUN mode (no data will be loaded)"
        docker compose run --rm "$ETL_SERVICE" python -m etl_pipeline.main --env "$ETL_ENV" --dry-run
    else
        if run_etl_pipeline "$ETL_ENV"; then
            show_results
            print_header "Pipeline Execution Complete"
            print_success "ETL pipeline finished successfully!"
            echo ""
            print_info "Next steps:"
            echo "  - View logs: docker compose logs $ETL_SERVICE"
            echo "  - Query database: docker compose exec $DB_SERVICE psql -U postgres -d vector_db"
            echo "  - Stop database: docker compose stop $DB_SERVICE"
        else
            print_error "Pipeline execution failed. Check logs for details."
            exit 1
        fi
    fi
}

# Run main function
main "$@"

