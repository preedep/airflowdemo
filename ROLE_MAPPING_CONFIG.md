# Role Mapping Configuration

This document explains how to configure role mapping for Azure AD OAuth authentication in Airflow.

## Configuration Options

The `ROLE_MAPPING_METHOD` environment variable controls how Azure AD claims are mapped to Airflow roles:

- `role` (**default**): Uses the `roles` claim from the Azure AD token
- `group`: Uses the `groups` claim from the Azure AD token

**Note**: If `ROLE_MAPPING_METHOD` is not set, the system will automatically use `role` mapping.

## Setting the Configuration

### Option 1: Role-based Mapping (Default)
```bash
# This is the default - no need to set if you want role mapping
export ROLE_MAPPING_METHOD=role

# Or simply don't set the variable at all (uses default)
# unset ROLE_MAPPING_METHOD
```

### Option 2: Group-based Mapping
```bash
export ROLE_MAPPING_METHOD=group
```

## Mapping Definitions

### Role Mapping
Maps Azure AD App Roles to Airflow roles:
```python
role_mapping = {
    "Airflow.Admin": "Admin",
    "Airflow.Viewer": "Viewer", 
    "Airflow.ProjectA": "ProjectA",
    "Airflow.ProjectB": "ProjectB",
}
```

### Group Mapping
Maps Azure AD Group IDs to Airflow roles:
```python
group_mapping = {
    "87759d0d-0948-4154-b5cc-0d9aa690c0d5": "Admin",
    "87b76a76-2c08-4c49-aca6-830177ac6ae3": "ProjectA",
    "22db4534-9819-444c-9b3b-6e53bf3c530e": "Viewer",
    "8fc5f04b-d8fe-4272-87f8-926c5c2b1d93": "ProjectB"
}
```

## Example Token Claims

### Sample ID Token with both roles and groups:
```json
{
  "aud": "71668a56-2d68-4a47-b707-81f10c76f88f",
  "iss": "https://login.microsoftonline.com/5612aad0-a1b7-4391-87a7-389e38e63b73/v2.0",
  "groups": [
    "22db4534-9819-444c-9b3b-6e53bf3c530e",
    "8fc5f04b-d8fe-4272-87f8-926c5c2b1d93",
    "87b76a76-2c08-4c49-aca6-830177ac6ae3"
  ],
  "roles": [
    "Airflow.ProjectA"
  ],
  "name": "NixDev001",
  "preferred_username": "nixdev001@NICKDEV001.onmicrosoft.com"
}
```

## Behavior Examples

### With ROLE_MAPPING_METHOD=role
- Token contains `"roles": ["Airflow.ProjectA"]`
- Result: User gets `ProjectA` role in Airflow

### With ROLE_MAPPING_METHOD=group  
- Token contains `"groups": ["87b76a76-2c08-4c49-aca6-830177ac6ae3"]`
- Result: User gets `ProjectA` role in Airflow (based on group mapping)

## Docker Compose Example

```yaml
services:
  airflow-webserver:
    environment:
      - ROLE_MAPPING_METHOD=group  # or 'role'
      - AZURE_TENANT_ID=your-tenant-id
      - AZURE_CLIENT_ID=your-client-id
      - AZURE_CLIENT_SECRET=your-client-secret
```

## Logging

The system will log which mapping method is being used:
```
[OAUTH CONFIG] ROLE_MAPPING_METHOD=group
🔐 Using mapping method: group
🔐 [GROUP] Mapped '87b76a76-2c08-4c49-aca6-830177ac6ae3' -> 'ProjectA'
```
