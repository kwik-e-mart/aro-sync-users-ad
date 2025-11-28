#!/bin/bash

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to be ready..."
sleep 5

BUCKET=sync-bucket

# Create S3 bucket
echo "Creating S3 bucket: $BUCKET"
awslocal s3 mb s3://$BUCKET

# Create directory structure
echo "Creating directory structure in S3..."
awslocal s3api put-object --bucket $BUCKET --key input/
awslocal s3api put-object --bucket $BUCKET --key results/

# Upload sample files if they exist
if [ -f /tmp/sample-ad-users.csv ]; then
  echo "Uploading sample AD users file..."
  awslocal s3 cp /tmp/sample-ad-users.csv s3://$BUCKET/input/users.csv
fi

if [ -f /tmp/sample-mapping.csv ]; then
  echo "Uploading sample mapping file..."
  awslocal s3 cp /tmp/sample-mapping.csv s3://$BUCKET/input/mapping.csv
fi

echo "LocalStack S3 initialization complete!"
echo "Bucket contents:"
awslocal s3 ls s3://$BUCKET --recursive
