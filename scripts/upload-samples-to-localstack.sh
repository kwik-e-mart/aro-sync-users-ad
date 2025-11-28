#!/bin/bash

# Script to upload sample CSV files to LocalStack S3
# Run this after starting LocalStack with docker-compose

echo "Uploading sample files to LocalStack S3..."

# Set LocalStack endpoint
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
ENDPOINT_URL=http://localhost:4566
BUCKET=sync-bucket

# Create bucket if it doesn't exist
echo "Creating bucket $BUCKET..."
aws --endpoint-url=$ENDPOINT_URL s3 mb s3://$BUCKET 2>/dev/null || echo "Bucket already exists"

# Upload AD users file
echo "Uploading sample-data/users.csv..."
aws --endpoint-url=$ENDPOINT_URL s3 cp sample-data/users.csv s3://$BUCKET/input/users.csv
# Upload mapping file
echo "Uploading sample-data/mapping.csv..."
aws --endpoint-url=$ENDPOINT_URL s3 cp sample-data/mapping.csv s3://$BUCKET/input/mapping.csv

# List files
echo ""
echo "Files in S3 bucket:"
aws --endpoint-url=$ENDPOINT_URL s3 ls s3://$BUCKET --recursive

echo ""
echo "✓ Sample files uploaded successfully!"
echo ""
echo "You can now test the API with:"
echo "  curl -X POST 'http://localhost:8080/sync-from-s3?dry_run=true'"
