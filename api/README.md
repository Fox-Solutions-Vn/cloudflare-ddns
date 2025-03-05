# Cloudflare Config Manager API

This FastAPI application provides a REST API to manage Cloudflare configurations.

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
uvicorn api.main:app --reload
```

## API Endpoints

### Accounts
- `GET /accounts` - Get all Cloudflare accounts
- `POST /accounts` - Add a new account
- `GET /accounts/{account_id}` - Get a specific account
- `PUT /accounts/{account_id}` - Update an account
- `DELETE /accounts/{account_id}` - Delete an account

### Authentication
- `PUT /accounts/{account_id}/auth` - Update account authentication

### Zones
- `GET /accounts/{account_id}/zones` - Get zones for an account
- `POST /accounts/{account_id}/zones` - Add a new zone to an account
- `GET /accounts/{account_id}/zones/{zone_id}` - Get a specific zone
- `PUT /accounts/{account_id}/zones/{zone_id}` - Update a zone
- `DELETE /accounts/{account_id}/zones/{zone_id}` - Delete a zone

## Data Validation

The API includes comprehensive validation:

### Subdomain
- Name must be a valid DNS subdomain (alphanumeric with hyphens, max 63 chars)
- Each subdomain has a unique ID

### Zone
- Zone ID must be a 32-character hexadecimal string
- Each zone has a unique ID

### Authentication
- Can use API token and/or API key
- At least one authentication method is required
- API key requires a valid email address
- No empty authentication values allowed

### TTL
- Must be between 60 and 86400 seconds (1 minute to 24 hours)

## Example Usage

### Add a new account with API token only
```bash
curl -X POST "http://localhost:8000/accounts" -H "Content-Type: application/json" -d '{
  "authentication": {
    "api_token": "your_api_token"
  },
  "zones": []
}'
```

### Add a new account with API key only
```bash
curl -X POST "http://localhost:8000/accounts" -H "Content-Type: application/json" -d '{
  "authentication": {
    "api_key": {
      "api_key": "your_api_key",
      "account_email": "your_email@example.com"
    }
  },
  "zones": []
}'
```

### Add a new account with both authentication methods
```bash
curl -X POST "http://localhost:8000/accounts" -H "Content-Type: application/json" -d '{
  "authentication": {
    "api_token": "your_api_token",
    "api_key": {
      "api_key": "your_api_key",
      "account_email": "your_email@example.com"
    }
  },
  "zones": []
}'
```

### Add a zone to an account
```bash
curl -X POST "http://localhost:8000/accounts/YOUR_ACCOUNT_ID/zones" -H "Content-Type: application/json" -d '{
  "zone_id": "0123456789abcdef0123456789abcdef",
  "subdomains": [
    {
      "name": "subdomain1",
      "proxied": true
    }
  ]
}'
```

For more details and interactive API documentation, visit http://localhost:8000/docs after starting the server.
