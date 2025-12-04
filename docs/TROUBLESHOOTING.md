# Troubleshooting Guide

Common issues and solutions for the AD User Sync API with LocalStack.

## LocalStack Issues

### Error: Device or resource busy

**Error Message:**
```
ERROR: 'rm -rf "/tmp/localstack"': exit code 1
ERROR: Device or resource busy: '/tmp/localstack'
```

**Cause:** Volume mount conflict between LocalStack and the host system.

**Solution:**

1. Stop and remove containers:
   ```bash
   docker-compose down -v
   ```

2. Remove local directory (if exists):
   ```bash
   rm -rf localstack-data
   ```

3. The docker-compose.yml has been fixed to use Docker named volumes instead of bind mounts:
   ```yaml
   volumes:
     - "localstack-data:/var/lib/localstack"  # ✓ Named volume
   ```

4. Start services:
   ```bash
   docker-compose up -d
   ```

### LocalStack Not Starting

**Symptoms:**
- Container exits immediately
- No LocalStack logs

**Solution:**

1. Check logs:
   ```bash
   docker-compose logs localstack
   ```

2. Restart LocalStack:
   ```bash
   docker-compose restart localstack
   ```

3. If still failing, rebuild:
   ```bash
   docker-compose down -v
   docker-compose up -d --build
   ```

### S3 Bucket Not Created

**Symptoms:**
- API returns "bucket does not exist"
- No files in S3

**Solution:**

1. Check init script ran:
   ```bash
   docker-compose logs localstack | grep "initialization complete"
   ```

2. Manually create bucket:
   ```bash
   aws --endpoint-url=http://localhost:4566 s3 mb s3://sync-bucket
   ```

3. Upload files:
   ```bash
   ./upload-samples-to-localstack.sh
   ```

## Application Issues

### Application Can't Connect to LocalStack

**Error:**
```
Error fetching files from S3: Could not connect to the endpoint URL
```

**Cause:** Wrong endpoint URL or network issue.

**Solution:**

1. Inside Docker Compose network, use service name:
   ```yaml
   AWS_ENDPOINT_URL=http://localstack:4566  # ✓ Inside Docker
   ```

2. From host machine, use localhost:
   ```bash
   AWS_ENDPOINT_URL=http://localhost:4566   # ✓ Outside Docker
   ```

3. Check network connectivity:
   ```bash
   docker-compose exec app curl http://localstack:4566/_localstack/health
   ```

### Files Not Found in S3

**Error:**
```
Error fetching files from S3: The specified key does not exist
```

**Solution:**

1. List bucket contents:
   ```bash
   aws --endpoint-url=http://localhost:4566 s3 ls s3://sync-bucket/input/
   ```

2. Upload sample files:
   ```bash
   ./upload-samples-to-localstack.sh
   ```

3. Verify file paths in `.env`:
   ```bash
   S3_AD_USERS_FILE=input/users.csv
   S3_MAPPING_FILE=input/mapping.csv
   ```

### Access Denied Errors

**Error:**
```
Error fetching files from S3: Access Denied
```

**Solution:**

For LocalStack, ensure test credentials are set:
```bash
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
```

For real AWS, check IAM permissions.

## Docker Issues

### Port Already in Use

**Error:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:4566: bind: address already in use
```

**Solution:**

1. Find process using port:
   ```bash
   lsof -i :4566
   ```

2. Kill the process or change port in docker-compose.yml:
   ```yaml
   ports:
     - "14566:4566"  # Use different host port
   ```

3. Update AWS_ENDPOINT_URL accordingly.

### Container Keeps Restarting

**Solution:**

1. Check logs:
   ```bash
   docker-compose logs app
   ```

2. Common causes:
   - Missing environment variables
   - Application crash on startup
   - Invalid configuration

3. Check environment variables:
   ```bash
   docker-compose config
   ```

## Configuration Issues

### Missing Environment Variables

**Error:**
```
ValidationError: Field required
```

**Solution:**

1. Ensure `.env` file exists:
   ```bash
   cp .env.example .env
   ```

2. Set required variables:
   ```bash
   NULLPLATFORM_API_KEY=your_key
   ORGANIZATION_ID=your_org_id
   S3_BUCKET=sync-bucket
   S3_AD_USERS_FILE=input/users.csv
   S3_MAPPING_FILE=input/mapping.csv
   ```

3. For LocalStack, also set:
   ```bash
   AWS_ENDPOINT_URL=http://localhost:4566
   AWS_ACCESS_KEY_ID=test
   AWS_SECRET_ACCESS_KEY=test
   ```

### Invalid CSV Format

**Error:**
```
Error parsing CSV: ...
```

**Solution:**

1. Check CSV headers match exactly:
   - AD Users: `Nombre,Correo,Grupo`
   - Mapping: `grupo,nrn,roles`

2. Ensure no extra spaces in headers

3. Check file encoding (UTF-8)

4. Validate with sample files:
   ```bash
   cat sample-data/users.csv
   cat sample-data/mapping.csv
   ```

## Network Issues

### Can't Access API from Host

**Solution:**

1. Check container is running:
   ```bash
   docker-compose ps
   ```

2. Check port mapping:
   ```bash
   docker port sync-app
   ```

3. Test from inside container:
   ```bash
   docker-compose exec app curl http://localhost:8080/health
   ```

4. Test from host:
   ```bash
   curl http://localhost:8080/health
   ```

### Containers Can't Communicate

**Solution:**

1. Check network:
   ```bash
   docker network ls | grep sync
   docker network inspect sync-users-ad_sync-network
   ```

2. Ensure containers are on same network in docker-compose.yml

3. Restart networking:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Data Persistence Issues

### Data Lost After Restart

**Solution:**

Named volumes are used for persistence. To verify:

```bash
# Check volume exists
docker volume ls | grep localstack-data

# Inspect volume
docker volume inspect sync-users-ad_localstack-data
```

Data persists between container restarts but is lost with `docker-compose down -v`.

### Clear All Data

To start fresh:

```bash
# Stop and remove everything
docker-compose down -v

# Start fresh
docker-compose up -d

# Re-upload sample files
./upload-samples-to-localstack.sh
```

## Performance Issues

### Slow Response Times

**Solution:**

1. Check container resources:
   ```bash
   docker stats
   ```

2. Increase Docker resources in Docker Desktop settings

3. Check LocalStack logs for issues:
   ```bash
   docker-compose logs localstack | tail -50
   ```

## Debugging Tips

### Enable Debug Logging

1. LocalStack:
   Already enabled with `DEBUG=1` in docker-compose.yml

2. Application:
   Add to docker-compose.yml app service:
   ```yaml
   environment:
     - LOG_LEVEL=DEBUG
   ```

### View Real-Time Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f localstack

# Last 100 lines
docker-compose logs --tail=100
```

### Inspect Container

```bash
# Get shell in container
docker-compose exec app /bin/sh

# Check environment variables
docker-compose exec app env

# Test connectivity
docker-compose exec app curl http://localstack:4566/_localstack/health
```

### Test S3 Directly

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
ENDPOINT=http://localhost:4566

# List buckets
aws --endpoint-url=$ENDPOINT s3 ls

# List objects
aws --endpoint-url=$ENDPOINT s3 ls s3://sync-bucket --recursive

# Download file
aws --endpoint-url=$ENDPOINT s3 cp s3://sync-bucket/input/users.csv -

# Upload file
aws --endpoint-url=$ENDPOINT s3 cp test.csv s3://sync-bucket/input/test.csv
```

## Getting Help

If you still have issues:

1. Check logs: `docker-compose logs -f`
2. Verify configuration: `docker-compose config`
3. Test connectivity: `curl http://localhost:8080/health`
4. Check LocalStack health: `curl http://localhost:4566/_localstack/health`
5. Review environment variables: `docker-compose exec app env | grep -E '(S3|AWS)'`

## Clean Slate

If all else fails, start completely fresh:

```bash
# Stop everything
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Remove any leftover data
rm -rf localstack-data

# Rebuild and start
docker-compose up -d --build

# Wait for services to be ready
sleep 10

# Upload sample files
./upload-samples-to-localstack.sh

# Test
curl http://localhost:8080/health
curl -X POST "http://localhost:8080/sync-from-s3?dry_run=true"
```
