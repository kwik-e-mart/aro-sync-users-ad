#!/bin/sh
#
# Cron job script to trigger the sync endpoint
# This script is designed to be run as a Kubernetes CronJob or similar scheduler
#
# Required environment variables:
# - SYNC_API_URL: The URL of the sync API endpoint (e.g., http://sync-api-service:8080)
# - API_SECRET_KEY: The shared API key for authentication
#

set -e

# Get the API URL from environment variable or use default
SYNC_API_URL=${SYNC_API_URL:-http://localhost:8080}
ENDPOINT="${SYNC_API_URL}/sync-from-s3"

# Check if API_SECRET_KEY is set
if [ -z "$API_SECRET_KEY" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: API_SECRET_KEY environment variable is not set"
    exit 1
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Triggering sync at: ${ENDPOINT}"

# Make the API call with authentication header and capture response
RESPONSE=$(curl -s -X POST "${ENDPOINT}" \
    -H "X-API-Key: ${API_SECRET_KEY}" \
    -w "\n%{http_code}" || echo "000")

# Extract HTTP status code (last line) and body (all lines except last)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

# Log the response
echo "HTTP Status: ${HTTP_CODE}"
echo "Response: ${BODY}"

# Parse and pretty print if jq is available
if command -v jq >/dev/null 2>&1; then
    echo "$BODY" | jq .
fi

# Check if the request was successful
if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Sync triggered successfully"
    exit 0
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: Sync failed with status ${HTTP_CODE}"
    exit 1
fi
