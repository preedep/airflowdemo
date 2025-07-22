#!/bin/bash

# Airflow Docker Compose Runner Script
# This script helps you manage your Airflow Docker setup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
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

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  up          Start Airflow services (default)"
    echo "  down        Stop and remove Airflow services"
    echo "  restart     Restart Airflow services"
    echo "  logs        Show logs from all services"
    echo "  status      Show status of all services"
    echo "  init        Initialize Airflow (run first time)"
    echo "  clean       Clean up everything (containers, volumes, networks)"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              # Start Airflow"
    echo "  $0 up           # Start Airflow"
    echo "  $0 down         # Stop Airflow"
    echo "  $0 logs         # Show logs"
    echo "  $0 clean        # Clean everything"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Function to check if docker-compose file exists
check_compose_file() {
    if [ ! -f "docker-compose.yaml" ]; then
        print_error "docker-compose.yaml not found in current directory"
        exit 1
    fi
}

# Function to create necessary directories
create_directories() {
    print_info "Creating necessary directories..."
    
    # List of required directories
    directories=("config" "dags" "logs" "plugins" "pg_data")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_info "Created directory: $dir"
        else
            print_info "Directory already exists: $dir"
        fi
    done
    
    print_success "All necessary directories are ready"
}

# Function to set environment variables
set_environment() {
    print_info "Setting up environment..."
    
    # Set AIRFLOW_UID if not already set
    if [ -z "$AIRFLOW_UID" ]; then
        export AIRFLOW_UID=$(id -u)
        print_info "AIRFLOW_UID set to $AIRFLOW_UID"
    fi
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        echo "AIRFLOW_UID=$AIRFLOW_UID" > .env
        print_info "Created .env file with AIRFLOW_UID=$AIRFLOW_UID"
    fi
}

# Function to initialize Airflow
init_airflow() {
    print_info "Initializing Airflow..."
    create_directories
    set_environment
    docker-compose up airflow-init
    print_success "Airflow initialized successfully"
}

# Function to start services
start_services() {
    print_info "Starting Airflow services..."
    create_directories
    set_environment
    docker-compose up -d
    print_success "Airflow services started"
    print_info "Airflow webserver will be available at: http://localhost:8080"
    print_info "Default login: admin / admin"
}

# Function to stop services
stop_services() {
    print_info "Stopping Airflow services..."
    docker-compose down
    print_success "Airflow services stopped"
}

# Function to restart services
restart_services() {
    print_info "Restarting Airflow services..."
    docker-compose down
    docker-compose up -d
    print_success "Airflow services restarted"
}

# Function to show logs
show_logs() {
    print_info "Showing logs from all services..."
    docker-compose logs -f
}

# Function to show status
show_status() {
    print_info "Showing status of all services..."
    docker-compose ps
}

# Function to clean everything
clean_all() {
    print_warning "This will remove all containers, volumes, and networks!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleaning up everything..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Main script logic
main() {
    check_docker
    check_compose_file
    
    case "${1:-up}" in
        "up"|"start")
            start_services
            ;;
        "down"|"stop")
            stop_services
            ;;
        "restart")
            restart_services
            ;;
        "logs")
            show_logs
            ;;
        "status"|"ps")
            show_status
            ;;
        "init")
            init_airflow
            ;;
        "clean")
            clean_all
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
