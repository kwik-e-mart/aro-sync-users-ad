.PHONY: help up down logs restart clean upload-samples test-sync test-dry-run build

# Default target
help:
	@echo "Available targets:"
	@echo "  up              - Start LocalStack and Application"
	@echo "  down            - Stop all services"
	@echo "  logs            - View logs from all services"
	@echo "  restart         - Restart all services"
	@echo "  clean           - Stop services and remove volumes"
	@echo "  build           - Rebuild Docker images"
	@echo "  upload-samples  - Upload sample CSV files to LocalStack"
	@echo "  test-dry-run    - Test sync with dry run"
	@echo "  test-sync       - Test actual sync"
	@echo "  test-cached     - Test cached result"
	@echo "  view-results    - View results in LocalStack S3"

# Start services
up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "✓ Services started!"
	@echo "  - LocalStack: http://localhost:4566"
	@echo "  - Application: http://localhost:8080"

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Restart services
restart:
	docker-compose restart

# Clean everything
clean:
	docker-compose down -v
	@echo "✓ All services stopped and volumes removed"

# Rebuild images
build:
	docker-compose build --no-cache

# Upload sample files
upload-samples:
	@./upload-samples-to-localstack.sh

# Test sync with dry run
test-dry-run:
	@echo "Testing sync with dry run..."
	@curl -s -X POST "http://localhost:8080/sync-from-s3?dry_run=true" | jq

# Test actual sync
test-sync:
	@echo "Running actual sync..."
	@curl -s -X POST "http://localhost:8080/sync-from-s3" | jq

# Test cached result
test-cached:
	@echo "Testing cached result..."
	@curl -s -X POST "http://localhost:8080/sync-from-s3" | jq '.status'

# View results in S3
view-results:
	@echo "Results in LocalStack S3:"
	@AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test aws --endpoint-url=http://localhost:4566 s3 ls s3://sync-bucket/results/

# Complete setup and test flow
setup: up upload-samples
	@echo ""
	@echo "✓ Setup complete! You can now test the API:"
	@echo "  make test-dry-run  # Test with dry run"
	@echo "  make test-sync     # Run actual sync"
	@echo "  make test-cached   # Test cached result"
