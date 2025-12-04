# S3 Integration

This document explains how to use the S3 integration for the AD User Sync API.

## Overview

The API now supports reading input CSV files from S3 and storing sync results back to S3. Results are cached based on MD5 hash of the input files to avoid redundant processing.

## Configuration

Add the following environment variables to your `.env` file:

```bash
# S3 Configuration
S3_BUCKET=my-ad-sync-bucket
S3_AD_USERS_FILE=input/users.csv
S3_MAPPING_FILE=input/mapping.csv
S3_RESULTS_PREFIX=results/
AWS_REGION=us-east-1
```

### Environment Variables

- `S3_BUCKET`: The name of your S3 bucket
- `S3_AD_USERS_FILE`: Path to the AD users CSV file within the bucket
- `S3_MAPPING_FILE`: Path to the group mapping CSV file within the bucket
- `S3_RESULTS_PREFIX`: Prefix for storing result files (default: `results/`)
- `AWS_REGION`: AWS region for the S3 bucket (default: `us-east-1`)

## AWS Credentials

The S3 service uses boto3, which will automatically use credentials from:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. AWS credentials file (`~/.aws/credentials`)
3. IAM role (if running on EC2/ECS/Lambda)

### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::my-ad-sync-bucket/input/*",
        "arn:aws:s3:::my-ad-sync-bucket/results/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-ad-sync-bucket"
      ]
    }
  ]
}
```

## API Endpoints

### POST /sync-from-s3

Sync users from CSV files stored in S3.

**Query Parameters:**
- `dry_run` (boolean, optional): If true, simulate changes without applying them. Default: `false`
- `force` (boolean, optional): If true, bypass cache and force re-run even if results exist. Default: `false`

**Example Usage:**

```bash
# Normal sync (with caching)
curl -X POST "http://localhost:8080/sync-from-s3"

# Dry run
curl -X POST "http://localhost:8080/sync-from-s3?dry_run=true"

# Force sync (bypass cache)
curl -X POST "http://localhost:8080/sync-from-s3?force=true"
```

**Response:**

```json
{
  "status": "success",
  "users_processed": 10,
  "users_created": 2,
  "users_deleted": 1,
  "users_updated": 3,
  "logs": [
    "Starting synchronization process in NORMAL mode...",
    "Parsed 10 AD users and 5 group mappings.",
    "...",
    "Synchronization completed.",
    "Result stored in S3: s3://my-ad-sync-bucket/results/abc123def456.json",
    "MD5 hash: abc123def456"
  ]
}
```

### POST /sync

Original endpoint for uploading files directly (still available).

## How Caching Works

1. When `/sync-from-s3` is called, the API:
   - Fetches the CSV files from S3
   - Calculates MD5 hash: `md5(ad_users_content + mapping_content)`
   - Checks if a result file exists: `s3://bucket/results/{md5}.json`

2. If result exists (and `force=false`):
   - Returns cached result with `status: "cached"`
   - Skips synchronization

3. If result doesn't exist (or `force=true`):
   - Executes synchronization
   - Stores result to S3: `s3://bucket/results/{md5}.json`

## S3 File Structure

```
my-ad-sync-bucket/
├── input/
│   ├── users.csv       # AD users file
│   └── mapping.csv        # Group mapping file
└── results/
    ├── abc123def456.json  # Result for specific input combination
    ├── 789xyz012345.json  # Result for another input combination
    └── ...
```

## CSV File Format

### AD Users File (users.csv)

```csv
Nombre,Correo,Grupo
John Doe,john@example.com,Group1
Jane Smith,jane@example.com,Group2
```

### Mapping File (mapping.csv)

```csv
grupo,nrn,roles
Group1,"nrn:app1,nrn:app2","admin,viewer"
Group2,"nrn:app2,nrn:app3",editor
```

## Testing

### Upload Test Files to S3

```bash
# Upload AD users file
aws s3 cp users.csv s3://my-ad-sync-bucket/input/users.csv

# Upload mapping file
aws s3 cp mapping.csv s3://my-ad-sync-bucket/input/mapping.csv
```

### Test the API

```bash
# Test with dry run
curl -X POST "http://localhost:8080/sync-from-s3?dry_run=true" | jq

# Run actual sync
curl -X POST "http://localhost:8080/sync-from-s3" | jq

# Check cached result (should return immediately)
curl -X POST "http://localhost:8080/sync-from-s3" | jq

# Force re-run (bypass cache)
curl -X POST "http://localhost:8080/sync-from-s3?force=true" | jq
```

### View Results in S3

```bash
# List all results
aws s3 ls s3://my-ad-sync-bucket/results/

# Download a specific result
aws s3 cp s3://my-ad-sync-bucket/results/abc123def456.json - | jq
```

## Error Handling

The API will return appropriate HTTP error codes:

- `500`: Internal server error (S3 access issues, sync failures, etc.)

Example error response:

```json
{
  "detail": "Error fetching files from S3: The specified bucket does not exist"
}
```

## Troubleshooting

### Files not found in S3

**Error:** `Error fetching files from S3: The specified key does not exist`

**Solution:** Verify the file paths in your `.env` file match the actual S3 object keys.

### Access denied

**Error:** `Error fetching files from S3: Access Denied`

**Solution:**
1. Check AWS credentials are configured
2. Verify IAM permissions allow `s3:GetObject` and `s3:PutObject`
3. Check S3 bucket policy

### Cached results not being used

**Issue:** API always re-runs sync even when files haven't changed

**Solution:** Ensure `force=false` (or omit the parameter) when calling the API.

### Results not stored in S3

**Issue:** Sync completes but no result file in S3

**Solution:**
1. Check you're not using `dry_run=true`
2. Verify IAM permissions allow `s3:PutObject` on the results prefix
3. Check API logs for errors during S3 upload
