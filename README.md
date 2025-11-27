# AD User Synchronization System

A FastAPI-based service for synchronizing Active Directory users and permissions with an internal authorization system.

## Overview

This application reads user data and group mappings from CSV files and synchronizes them with internal user and authorization repositories. It's designed to run as a Kubernetes CronJob and supports multiple execution modes.

## Features

- CSV-based user and group mapping ingestion
- Automatic user creation, update, and deletion
- Role synchronization based on AD group mappings
- Multiple execution modes (Dry Run, Normal, Force)
- RESTful API endpoints

## Prerequisites

- Python 3.11+
- Poetry (Python dependency manager)

## Installation

### 1. Install Poetry

If you don't have Poetry installed:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 2. Install Dependencies

```bash
poetry install
```

This will create a virtual environment and install all required dependencies.

### 3. Install Production Dependencies Only

```bash
poetry install --no-dev
```

## Configuration

Before running the application, you need to configure the required environment variables.

### Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your Nullplatform API key:

```bash
# Required
NULLPLATFORM_API_KEY=your_actual_api_key_here

# Optional (defaults provided)
AUTH_API_URL=https://auth.nullplatform.io
USERS_API_URL=https://users.nullplatform.io
```

## Running the Application

### Using Poetry

Activate the Poetry shell:

```bash
poetry shell
```

Run the FastAPI application:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Direct Execution with Poetry

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

## API Endpoints

### Health Check
```bash
GET /health
```
Returns: `{"status": "ok"}`

### Root
```bash
GET /
```
Returns: `{"message": "AD User Sync API is running"}`

### Sync Users
```bash
POST /sync
```
Upload two CSV files:
- `ad_users_file`: CSV with columns `Nombre`, `Correo`, `Grupo`
- `mapping_file`: CSV with columns `grupo`, `nrn`, `roles`

Query parameters:
- `dry_run` (boolean, default: false) - Simulate sync without making changes
- `force` (boolean, default: false) - Force sync mode (reserved for future use)

Example using curl:
```bash
curl -X POST "http://localhost:8080/sync" \
  -F "ad_users_file=@ad_users.csv" \
  -F "mapping_file=@group_mapping.csv"
```

Example with dry run:
```bash
curl -X POST "http://localhost:8080/sync?dry_run=true" \
  -F "ad_users_file=@ad_users.csv" \
  -F "mapping_file=@group_mapping.csv"
```

Example with force mode:
```bash
curl -X POST "http://localhost:8080/sync?force=true" \
  -F "ad_users_file=@ad_users.csv" \
  -F "mapping_file=@group_mapping.csv"
```

## Docker

### Build the Image

```bash
docker build -t ad-user-sync:latest .
```

### Run the Container

You must provide the required environment variables:

```bash
docker run -e NULLPLATFORM_API_KEY=your_key_here -p 8080:8080 ad-user-sync:latest
```

Or use an environment file:

```bash
docker run --env-file .env -p 8080:8080 ad-user-sync:latest
```

### Test the Health Endpoint

```bash
curl http://localhost:8080/health
```

## Development

### Add a New Dependency

```bash
poetry add <package-name>
```

### Add a Development Dependency

```bash
poetry add --group dev <package-name>
```

### Update Dependencies

```bash
poetry update
```

### List Installed Packages

```bash
poetry show
```

### Run Tests

```bash
poetry run pytest
```

## CSV File Format

### AD Users File (`ad_users.csv`)
```csv
Nombre,Correo,Grupo
Jose Miguel Murrieta,jose.murrieta@example.com,Developers
Edwin Garces,edwin.garces@example.com,Admins
```

### Group Mapping File (`group_mapping.csv`)
```csv
grupo,nrn,roles
Developers,organization=1612316954:account=1217921210:namespace=595266136,"developer,member"
Admins,organization=1612316954:account=1217921210:namespace=595266136,admin
```

**Note:** The `nrn` column contains the full Nullplatform NRN (Namespace Resource Name) in the format:
`organization={org_id}:account={account_id}:namespace={namespace_id}`

## Architecture

See [technical_proposal.md](technical_proposal.md) for detailed architecture documentation.

## Deployment

This application is designed to run as a Kubernetes CronJob. See the technical proposal for deployment architecture details.

## License

MIT
