# Quick Start Guide

Get the AD User Sync API running with LocalStack in under 5 minutes!

## Prerequisites

- Docker and Docker Compose
- AWS CLI (optional, for manual S3 operations)
- Make (optional, for using Makefile commands)

## Option 1: Using Make (Recommended)

```bash
# Start everything and upload sample data
make setup

# Test with dry run
make test-dry-run

# Run actual sync
make test-sync

# View results
make view-results

# Stop everything
make down
```

## Option 2: Manual Steps

### 1. Start Services

```bash
docker-compose up -d
```

Wait a few seconds for services to start.

### 2. Upload Sample Data

```bash
./upload-samples-to-localstack.sh
```

### 3. Test the API

```bash
# Dry run
curl -X POST "http://localhost:8080/sync-from-s3?dry_run=true" | jq

# Actual sync
curl -X POST "http://localhost:8080/sync-from-s3" | jq
```

## What's Running?

- **LocalStack S3**: http://localhost:4566
- **FastAPI Application**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

## S3 Structure

```
s3://sync-bucket/
├── input/
│   ├── users.csv     # AD users from your directory
│   └── mapping.csv      # Group to role mappings
└── results/
    └── {md5_hash}.json  # Sync results (cached)
```

## API Endpoints

### GET /health
Check if the API is running.

```bash
curl http://localhost:8080/health
```

### POST /sync-from-s3
Sync users from S3 files.

```bash
# Dry run (no changes)
curl -X POST "http://localhost:8080/sync-from-s3?dry_run=true"

# Actual sync
curl -X POST "http://localhost:8080/sync-from-s3"

# Force sync (bypass cache)
curl -X POST "http://localhost:8080/sync-from-s3?force=true"
```

### POST /sync
Upload files directly (alternative to S3).

```bash
curl -X POST "http://localhost:8080/sync" \
  -F "ad_users_file=@sample-data/users.csv" \
  -F "mapping_file=@sample-data/mapping.csv" \
  -F "dry_run=true"
```

## Common Tasks

### View S3 Contents

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
aws --endpoint-url=http://localhost:4566 s3 ls s3://sync-bucket --recursive
```

### View Sync Result

```bash
# List results
aws --endpoint-url=http://localhost:4566 s3 ls s3://sync-bucket/results/

# View a specific result
aws --endpoint-url=http://localhost:4566 s3 cp s3://sync-bucket/results/abc123.json - | jq
```

### Update CSV Files

```bash
# Edit the sample files
nano sample-data/users.csv
nano sample-data/mapping.csv

# Re-upload to S3
./upload-samples-to-localstack.sh

# Test again
curl -X POST "http://localhost:8080/sync-from-s3?dry_run=true" | jq
```

### View Logs

```bash
# All logs
docker-compose logs -f

# Application logs only
docker-compose logs -f app

# LocalStack logs only
docker-compose logs -f localstack
```

### Stop Services

```bash
# Stop but keep data
docker-compose down

# Stop and remove data
docker-compose down -v
```

## Expected Output

### Dry Run Response

```json
{
  "status": "success",
  "users_processed": 3,
  "users_created": 0,
  "users_deleted": 0,
  "users_updated": 3,
  "logs": [
    "Starting synchronization process in DRY RUN mode...",
    "DRY RUN MODE: No actual changes will be made to users or roles.",
    "Parsed 3 AD users and 2 group mappings.",
    "[DRY RUN] Would update user john.doe@example.com roles in NRN 'organization=1698562351:application=app1' from [] to ['developer', 'viewer'].",
    "..."
  ]
}
```

### Cached Response

```json
{
  "status": "cached",
  "users_processed": 3,
  "users_created": 0,
  "users_deleted": 0,
  "users_updated": 3,
  "logs": [
    "Result already exists for MD5: abc123def456",
    "Skipping synchronization. Use force=true to re-run.",
    "..."
  ]
}
```

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker ps

# Check logs
docker-compose logs

# Restart
docker-compose restart
```

### Can't connect to LocalStack

```bash
# Check LocalStack is running
curl http://localhost:4566/_localstack/health

# Restart LocalStack
docker-compose restart localstack
```

### Files not in S3

```bash
# Re-upload
./upload-samples-to-localstack.sh

# Or manually
aws --endpoint-url=http://localhost:4566 s3 cp sample-data/users.csv s3://sync-bucket/input/users.csv
```

## Next Steps

1. **Customize CSV files** in `sample-data/`
2. **Update NRN values** to match your organization
3. **Test different scenarios**:
   - Add new users
   - Remove users
   - Change roles
   - Multiple groups per user
4. **Review results** in S3
5. **Deploy to production** with real AWS S3

## Production Deployment

For production, update your `.env` file:

```bash
# Remove LocalStack endpoint
# AWS_ENDPOINT_URL=

# Use real AWS S3 bucket
S3_BUCKET=my-production-bucket

# Use real AWS credentials or IAM role
AWS_ACCESS_KEY_ID=<your-real-key>
AWS_SECRET_ACCESS_KEY=<your-real-secret>
```

## Documentation

- [LocalStack Setup Guide](LOCALSTACK_SETUP.md) - Detailed LocalStack information
- [S3 Integration Guide](S3_INTEGRATION.md) - S3 integration details
- [API Documentation](http://localhost:8080/docs) - Interactive API docs

## Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Review the documentation
3. Try restarting: `docker-compose restart`
