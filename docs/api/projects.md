# API: Projects

## Create project

```
POST /v1/projects
```

Body:

```json
{
  "name": "My Project",
  "owner_wallet": "0x..."
}
```

Returns project `id` and an `api_key`. **The `api_key` is only returned once.** Store it securely.

## Get project config

```
GET /v1/projects/{project_id}/config
```

Returns anchoring configuration:

```json
{
  "anchoring": {
    "execution_mode": "platform",
    "chains": [
      {
        "name": "flare",
        "contract": "0x...",
        "rpc_url": "https://flare-api.flare.network/ext/C/rpc",
        "explorer_base_url": "https://flare-explorer.flare.network"
      }
    ]
  }
}
```

## Update project config

```
PUT /v1/projects/{project_id}/config
```

Execution modes:

- `platform` (default): ProofRails platform wallet anchors on behalf of the project.
- `tenant`: Project provides its own anchor contract and calls `POST /v1/iso/confirm-anchor` after anchoring.

## API key management

```
POST /v1/auth/api-keys           # Create new key
GET  /v1/auth/api-keys           # List keys for project
DELETE /v1/auth/api-keys/{id}    # Revoke key
```

## Auth introspection

```
GET /v1/auth/me
```

Returns the current principal: project ID, role, and whether the request is from an admin key or a project key.
