# LocalStack Setup Guide

This guide explains how to run the AD User Sync API with LocalStack S3 for local development and testing.

## Prerequisites

- Docker and Docker Compose installed
- AWS CLI installed (for uploading test files)

## Quick Start

### 1. Start LocalStack and the Application

```bash
# Start all services (LocalStack + Application)
docker-compose up -d

# Check logs
docker-compose logs -f
```

This will start:
- **LocalStack** on `http://localhost:4566` (S3 service)
- **Application** on `http://localhost:8080`

### 2. Upload Sample Data to LocalStack S3

```bash
# Upload the sample CSV files
./upload-samples-to-localstack.sh
```

Or manually:

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# Create bucket
aws --endpoint-url=http://localhost:4566 s3 mb s3://sync-bucket

# Upload files
aws --endpoint-url=http://localhost:4566 s3 cp sample-data/users.csv s3://sync-bucket/input/users.csv
aws --endpoint-url=http://localhost:4566 s3 cp sample-data/mapping.csv s3://sync-bucket/input/mapping.csv

# List files
aws --endpoint-url=http://localhost:4566 s3 ls s3://sync-bucket --recursive
```

### 3. Test the API

```bash
# Dry run (no changes)
curl -X POST "http://localhost:8080/sync-from-s3?dry_run=true" | jq

# Actual sync
curl -X POST "http://localhost:8080/sync-from-s3" | jq

# Check cached result (should return immediately)
curl -X POST "http://localhost:8080/sync-from-s3" | jq

# Force re-run (bypass cache)
curl -X POST "http://localhost:8080/sync-from-s3?force=true" | jq
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
│                                                          │
│  ┌────────────────────┐      ┌─────────────────────┐   │
│  │   LocalStack       │      │   Application       │   │
│  │   (S3 Service)     │◄─────┤   (FastAPI)        │   │
│  │                    │      │                     │   │
│  │  Port: 4566        │      │   Port: 8080        │   │
│  └────────────────────┘      └─────────────────────┘   │
│           │                            │                 │
│           │                            │                 │
│           ▼                            ▼                 │
│  ┌────────────────────┐      ┌─────────────────────┐   │
│  │  S3 Bucket:        │      │  Nullplatform       │   │
│  │  sync-bucket.      │      │  APIs               │   │
│  │                    │      │  (External)         │   │
│  │  input/            │      └─────────────────────┘   │
│  │  results/          │                                 │
│  └────────────────────┘                                 │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

The application is configured via environment variables in `docker-compose.yml`:

```yaml
environment:
  # Nullplatform API
  - NULLPLATFORM_API_KEY=${NULLPLATFORM_API_KEY}
  - ORGANIZATION_ID=${ORGANIZATION_ID}

  # S3 Configuration
  - S3_BUCKET=sync-bucket
  - S3_AD_USERS_FILE=input/users.csv
  - S3_MAPPING_FILE=input/mapping.csv
  - S3_RESULTS_PREFIX=results/

  # AWS/LocalStack
  - AWS_REGION=us-east-1
  - AWS_ACCESS_KEY_ID=test
  - AWS_SECRET_ACCESS_KEY=test
  - AWS_ENDPOINT_URL=http://localstack:4566  # Points to LocalStack
```

### Local Development (without Docker)

If you want to run the application locally (outside Docker) and use LocalStack:

1. Start only LocalStack:
   ```bash
   docker-compose up localstack -d
   ```

2. Copy the LocalStack environment file:
   ```bash
   cp .env.localstack .env
   ```

3. Run the application:
   ```bash
   poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
   ```

4. Upload test files:
   ```bash
   ./upload-samples-to-localstack.sh
   ```

## Sample Data

### AD Users CSV (`sample-data/users.csv`)

```csv
Nombre,Correo,Grupo
John Doe,john.doe@example.com,Developers
Jane Smith,jane.smith@example.com,Admins
Bob Wilson,bob.wilson@example.com,Developers
```

### Mapping CSV (`sample-data/mapping.csv`)

```csv
grupo,nrn,roles
Developers,"organization=1698562351:application=app1,organization=1698562351:application=app2","developer,viewer"
Admins,"organization=1698562351:application=app1",admin
```

## Useful Commands

### Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f app
docker-compose logs -f localstack

# Restart a service
docker-compose restart app

# Rebuild and restart
docker-compose up -d --build
```

### LocalStack S3 Commands

```bash
# Set environment for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
ENDPOINT=http://localhost:4566

# List buckets
aws --endpoint-url=$ENDPOINT s3 ls

# List objects in bucket
aws --endpoint-url=$ENDPOINT s3 ls s3://sync-bucket --recursive

# Download a file
aws --endpoint-url=$ENDPOINT s3 cp s3://sync-bucket/results/abc123.json ./result.json

# Delete a file
aws --endpoint-url=$ENDPOINT s3 rm s3://sync-bucket/results/abc123.json

# View file content
aws --endpoint-url=$ENDPOINT s3 cp s3://sync-bucket/results/abc123.json - | jq
```

### Testing Caching

```bash
# First run - will execute sync
curl -X POST "http://localhost:8080/sync-from-s3" | jq

# Second run - should return cached result
curl -X POST "http://localhost:8080/sync-from-s3" | jq '.status'
# Output: "cached"

# Modify a CSV file to change MD5
aws --endpoint-url=http://localhost:4566 s3 cp sample-data/users.csv s3://sync-bucket/input/users.csv

# Now it will re-run (different MD5)
curl -X POST "http://localhost:8080/sync-from-s3" | jq '.status'
# Output: "success"
```

## Troubleshooting

### LocalStack not starting

```bash
# Check LocalStack logs
docker-compose logs localstack

# Restart LocalStack
docker-compose restart localstack
```

### Application can't connect to LocalStack

**Issue:** Application shows `Connection refused` errors

**Solution:**
- Inside Docker Compose, use `http://localstack:4566`
- Outside Docker (local dev), use `http://localhost:4566`

### Files not found in S3

```bash
# Verify files exist
aws --endpoint-url=http://localhost:4566 s3 ls s3://sync-bucket/input/

# Re-upload files
./upload-samples-to-localstack.sh
```

### Permission errors

LocalStack uses test credentials by default:
- Access Key: `test`
- Secret Key: `test`

These should already be configured in the environment variables.

## Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (deletes all S3 data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Production vs LocalStack

### LocalStack (Development)

```bash
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

### AWS (Production)

```bash
# Remove AWS_ENDPOINT_URL or set to empty
AWS_ENDPOINT_URL=

# Use real AWS credentials
AWS_ACCESS_KEY_ID=<your-real-access-key>
AWS_SECRET_ACCESS_KEY=<your-real-secret-key>

# Or use IAM role (recommended for EC2/ECS/Lambda)
# No need to set credentials if using IAM role
```

## Next Steps

- Customize sample CSV files in `sample-data/`
- Modify NRN values in mapping.csv to match your organization
- Test different scenarios (new users, role changes, deletions)
- Monitor results in LocalStack S3: `s3://sync-bucket/results/`
