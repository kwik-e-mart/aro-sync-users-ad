# AD User Synchronization System with SCIM 2.0 Support

A FastAPI-based service for synchronizing Active Directory users and permissions with an internal authorization system. Supports both CSV-based batch synchronization and real-time SCIM 2.0 provisioning.

## Overview

This application provides two modes of operation:

1. **CSV Batch Sync**: Reads user data and group mappings from CSV files and synchronizes them with nullplatform
2. **SCIM 2.0 API**: Enables real-time user and group provisioning via the SCIM 2.0 protocol (RFC 7643/7644)

It's designed to run as a Kubernetes CronJob for batch operations while also exposing SCIM endpoints for identity provider integrations.

## Features

- CSV-based user and group mapping ingestion
- Automatic user creation, update, and deletion
- Role synchronization based on AD group mappings
- Multiple execution modes (Dry Run, Normal, Force)
- RESTful API endpoints
- **SCIM 2.0 Protocol Support**:
  - User provisioning (create, read, update, delete)
  - Group management
  - Filtering and pagination
  - Service Provider Configuration discovery
  - Compatible with Azure AD, Okta, OneLogin, and other SCIM clients

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

**Authentication Required**: All sync endpoints require an API key for authentication. Include the `X-API-Key` header in your requests.

Example using curl:
```bash
curl -X POST "http://localhost:8080/sync" \
  -H "X-API-Key: your-secret-key-here" \
  -F "ad_users_file=@users.csv" \
  -F "mapping_file=@group_mapping.csv"
```

Example with dry run:
```bash
curl -X POST "http://localhost:8080/sync?dry_run=true" \
  -H "X-API-Key: your-secret-key-here" \
  -F "ad_users_file=@users.csv" \
  -F "mapping_file=@group_mapping.csv"
```

Example with force mode:
```bash
curl -X POST "http://localhost:8080/sync?force=true" \
  -H "X-API-Key: your-secret-key-here" \
  -F "ad_users_file=@users.csv" \
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

### AD Users File (`users.csv`)
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
OrgViewers,*,"viewer,member"
```

**NRN Column Format:**

The `nrn` column can contain:
1. **Full NRN**: Specific Nullplatform NRN (Namespace Resource Name)
   - Format: `organization={org_id}:account={account_id}:namespace={namespace_id}`
   - Example: `organization=1612316954:account=1217921210:namespace=595266136`

2. **Multiple NRNs**: Comma-separated list of NRNs
   - Format: `nrn1,nrn2,nrn3`
   - Example: `organization=123:account=456,organization=123:namespace=789`

3. **Wildcard (`*`)**: Organization-level access
   - When you use `*`, it automatically resolves to `organization={ORGANIZATION_ID}`
   - Use this for users who need organization-wide access
   - Example: `*` → resolves to `organization=1850605908` (based on your ORGANIZATION_ID env var)

## SCIM 2.0 API

This application implements the SCIM 2.0 protocol for real-time user and group provisioning. The SCIM API allows identity providers (like Azure AD, Okta, OneLogin) to automatically provision users and manage their group memberships.

### SCIM Base URL

```
https://your-domain.com/scim/v2
```

### Authentication

All SCIM endpoints require authentication using the `X-API-Key` header (same as the sync endpoints).

```bash
curl -H "X-API-Key: your-secret-key-here" \
  https://your-domain.com/scim/v2/Users
```

### Service Provider Configuration

Get SCIM capabilities:

```bash
GET /scim/v2/ServiceProviderConfig
```

Get available resource types:

```bash
GET /scim/v2/ResourceTypes
```

### User Operations

#### List Users

```bash
GET /scim/v2/Users?startIndex=1&count=100
```

With filtering:

```bash
GET /scim/v2/Users?filter=userName eq "user@example.com"
```

#### Get User

```bash
GET /scim/v2/Users/{user-id}
```

#### Create User

```bash
POST /scim/v2/Users
Content-Type: application/json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "john.doe@example.com",
  "name": {
    "givenName": "John",
    "familyName": "Doe"
  },
  "emails": [
    {
      "value": "john.doe@example.com",
      "type": "work",
      "primary": true
    }
  ],
  "active": true,
  "groups": [
    {
      "value": "Developers"
    }
  ]
}
```

#### Update User (Full Replacement)

```bash
PUT /scim/v2/Users/{user-id}
Content-Type: application/json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
  "userName": "john.doe@example.com",
  "active": true,
  "groups": [
    {
      "value": "Developers"
    },
    {
      "value": "Admins"
    }
  ]
}
```

#### Patch User (Partial Update)

Deactivate a user:

```bash
PATCH /scim/v2/Users/{user-id}
Content-Type: application/json

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {
      "op": "replace",
      "path": "active",
      "value": false
    }
  ]
}
```

#### Delete User

```bash
DELETE /scim/v2/Users/{user-id}
```

### Group Operations

Groups are defined by the mapping CSV file. The SCIM API uses the `grupo` column values as group names.

#### List Groups

```bash
GET /scim/v2/Groups?startIndex=1&count=100
```

With filtering:

```bash
GET /scim/v2/Groups?filter=displayName eq "Developers"
```

#### Get Group

```bash
GET /scim/v2/Groups/{group-name}
```

Example:

```bash
GET /scim/v2/Groups/Developers
```

#### Update Group (Add/Remove Members)

```bash
PUT /scim/v2/Groups/Developers
Content-Type: application/json

{
  "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
  "displayName": "Developers",
  "members": [
    {
      "value": "user-id-1"
    },
    {
      "value": "user-id-2"
    }
  ]
}
```

#### Patch Group (Add Member)

```bash
PATCH /scim/v2/Groups/Developers
Content-Type: application/json

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {
      "op": "add",
      "path": "members",
      "value": [
        {
          "value": "user-id-3"
        }
      ]
    }
  ]
}
```

#### Patch Group (Remove Member)

```bash
PATCH /scim/v2/Groups/Developers
Content-Type: application/json

{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    {
      "op": "remove",
      "path": "members[value eq \"user-id-3\"]"
    }
  ]
}
```

### Configuring Identity Providers

#### Azure AD

1. In Azure AD, go to Enterprise Applications
2. Create a new application (Non-gallery application)
3. Go to Provisioning and set Mode to "Automatic"
4. Configure:
   - Tenant URL: `https://your-domain.com/scim/v2`
   - Secret Token: Your API key
5. Test connection and save
6. Map Azure AD attributes to SCIM attributes if needed
7. Start provisioning

#### Okta

1. In Okta Admin, go to Applications
2. Create a new app integration (SCIM 2.0)
3. Configure:
   - SCIM Base URL: `https://your-domain.com/scim/v2`
   - Authentication: HTTP Header
   - Authorization: `X-API-Key: your-secret-key-here`
4. Enable provisioning features (Create Users, Update User Attributes, Deactivate Users)
5. Configure attribute mappings
6. Assign users to the application

#### OneLogin

1. In OneLogin, go to Applications
2. Add a SCIM Provisioner with API Connection
3. Configure:
   - SCIM Base URL: `https://your-domain.com/scim/v2`
   - SCIM Bearer Token: Your API key (use as custom header: `X-API-Key`)
4. Map attributes
5. Enable provisioning and assign users

### How SCIM Works with Group Mappings

The SCIM implementation uses the **same mapping CSV file** as the batch sync to determine which nullplatform roles and NRNs to assign based on group membership:

1. The mapping file is loaded from S3 on application startup
2. When a user is added to a group via SCIM, the service looks up the group in the mapping
3. The corresponding roles and NRNs are automatically applied to the user in nullplatform
4. When a user is removed from a group, those roles are revoked

**Example mapping.csv:**

```csv
grupo,nrn,roles
Developers,organization=1612316954:account=1217921210:namespace=595266136,"developer,member"
Admins,organization=1612316954:account=1217921210:namespace=595266136,admin
OrgViewers,*,"viewer,member"
```

With this mapping:
- Adding a user to the "Developers" group via SCIM grants them `developer` and `member` roles in the specified namespace
- Adding a user to "OrgViewers" grants organization-level `viewer` and `member` roles

### SCIM and CSV Sync Interoperability

Both the SCIM API and CSV batch sync can be used together:

- **SCIM**: Real-time provisioning triggered by identity provider events
- **CSV Sync**: Periodic batch reconciliation to ensure consistency

The batch sync will respect changes made via SCIM and vice versa. They both work against the same nullplatform user and authorization repositories.

## Architecture

See [technical_proposal.md](technical_proposal.md) for detailed architecture documentation.

## Deployment

This application is designed to run as a Kubernetes CronJob for batch sync operations while also running as a persistent service to handle SCIM API requests. See the technical proposal for deployment architecture details.

## License

MIT
