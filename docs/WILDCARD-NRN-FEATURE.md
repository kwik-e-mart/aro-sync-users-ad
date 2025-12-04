# Wildcard NRN Feature

## Overview

The synchronization service now supports a wildcard (`*`) value in the NRN column of the mapping CSV file. This allows you to assign organization-level permissions to users without having to specify the full organization NRN.

## How It Works

When the sync service encounters an NRN value of `*`, it automatically resolves it to:

```
organization={ORGANIZATION_ID}
```

Where `ORGANIZATION_ID` comes from the `ORGANIZATION_ID` environment variable configured in your deployment.

## Use Cases

### 1. Organization-Wide Viewers
Give a group of users read-only access across the entire organization:

```csv
grupo,nrn,roles
AllViewers,*,"viewer,member"
```

### 2. Organization Administrators
Grant admin access at the organization level:

```csv
grupo,nrn,roles
OrgAdmins,*,admin
```

### 3. Mixed Access Levels
Combine wildcard with specific NRNs for users who need both organization-wide and specific resource access:

```csv
grupo,nrn,roles
PowerUsers,"*,organization=123:account=456:namespace=789","admin,developer"
```

## Example

### Input CSV (mapping.csv)
```csv
grupo,nrn,roles
Developers,organization=1850605908:account=56492458:namespace=12345,"developer,member"
OrgViewers,*,"viewer,member"
```

### Resolution Process

For a user in the "OrgViewers" group with `ORGANIZATION_ID=1850605908`:

1. The sync service reads the NRN value: `*`
2. It detects the wildcard
3. It resolves to: `organization=1850605908`
4. Assigns the roles `viewer,member` to this NRN

### Log Output

When a wildcard is resolved, you'll see a log entry like:

```
Resolved wildcard NRN '*' to 'organization=1850605908' for user john.doe@example.com
```

## Configuration

No additional configuration is required. The feature automatically uses your existing `ORGANIZATION_ID` environment variable:

```bash
# Set in your environment or .env file
ORGANIZATION_ID=1850605908
```

## Benefits

1. **Simplicity**: No need to remember or type the full organization NRN
2. **Portability**: Same CSV file works across different environments (dev/staging/prod)
3. **Maintainability**: Easy to identify organization-level permissions in your mapping file
4. **Flexibility**: Can combine with other NRNs for complex permission structures

## Implementation Details

The wildcard resolution is handled in the `SyncService._resolve_nrn()` method in `app/services.py`:

```python
def _resolve_nrn(self, nrn: str) -> str:
    """
    Resolve NRN value, replacing '*' wildcard with organization NRN.
    """
    if nrn.strip() == '*':
        from .config import config
        return f"organization={config.organization_id}"
    return nrn
```

This method is called for each NRN in the mapping CSV before storing it in the user's role assignments.
