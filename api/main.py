from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, model_validator, Field, ConfigDict
from typing import List, Optional, Dict, Any, Annotated
import json
from pathlib import Path
import uuid
import os
import re

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="web"), name="static")

# Config file path
CONFIG_FILE = Path("config.json")

def create_response(error: bool = False, data: Any = None, message: str = "") -> dict:
    return {
        "error": error,
        "data": data,
        "message": message
    }

@app.exception_handler(RequestValidationError) 
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field_path = " -> ".join(str(loc) for loc in error["loc"] if loc != "body")
        error_messages.append(f"Field '{field_path}': {error['msg']}")
    
    message = error_messages[0] if error_messages else "Validation Error"
    
    return JSONResponse(
        status_code=422,
        content={
            "error": True,
            "data": None,
            "message": message
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=create_response(
            error=True,
            data={"detail": str(exc.detail)},
            message="Error"
        )
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=create_response(
            error=True,
            data={"detail": str(exc)},
            message="Internal Server Error"
        )
    )

@app.get("/")
async def read_root():
    return FileResponse('web/index.html')

class ErrorResponse(BaseModel):
    error: bool = True
    message: str
    data: dict = None

class SuccessResponse(BaseModel):
    error: bool = False
    message: str
    data: dict = None

class SubDomain(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Annotated[str, Field(
        pattern=r"^[@a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
        description="Subdomain name, must be a valid domain name. Can include @ for root domain."
    )]
    proxied: bool = Field(default=False, description="Whether to proxy through Cloudflare")
    ttl: int = Field(default=1, ge=60, le=86400, description="TTL for DNS records (60-86400 seconds)")

    @model_validator(mode='after')
    def validate_subdomain(self) -> 'SubDomain':
        if len(self.name) > 63:
            raise ValueError("Subdomain name must be less than 63 characters")
        return self

    @model_validator(mode='after')
    def validate_ttl(self) -> 'SubDomain':
        if not (60 <= self.ttl <= 86400):
            raise ValueError("TTL must be between 60 and 86400 seconds")
        return self

class SubDomainCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: Annotated[str, Field(
        pattern=r"^[@a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$",
        description="Subdomain name, must be a valid domain name. Can include @ for root domain."
    )]
    proxied: bool = Field(default=False, description="Whether to proxy through Cloudflare")
    ttl: int = Field(default=1, ge=60, le=86400, description="TTL for DNS records (60-86400 seconds)")

    @model_validator(mode='after')
    def validate_subdomain(self) -> 'SubDomainCreate':
        if len(self.name) > 63:
            raise ValueError("Subdomain name must be less than 63 characters")
        return self

    @model_validator(mode='after')
    def validate_ttl(self) -> 'SubDomainCreate':
        if not (60 <= self.ttl <= 86400):
            raise ValueError("TTL must be between 60 and 86400 seconds")
        return self

class ZoneCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    zone_id: Annotated[str, Field(
        pattern=r'^[a-f0-9]{32}$',
        description="Cloudflare Zone ID (32 character hex string)"
    )]
    domain: str = Field(description="Domain name of the zone")
    subdomains: List[SubDomainCreate] = Field(default_factory=list)

class Zone(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    zone_id: Annotated[str, Field(
        pattern=r'^[a-f0-9]{32}$',
        description="Cloudflare Zone ID (32 character hex string)"
    )]
    domain: str = Field(description="Domain name of the zone")
    subdomains: List[SubDomain] = Field(default_factory=list, description="List of subdomains in this zone")

    @model_validator(mode='after')
    def validate_zone_id(self) -> 'Zone':
        if not re.match(r'^[a-f0-9]{32}$', self.zone_id):
            raise ValueError("Zone ID must be a 32-character hexadecimal string")
        return self
    
    @model_validator(mode='after')
    def validate_unique_subdomains(self) -> 'Zone':
        subdomain_names = set()
        for subdomain in self.subdomains:
            if subdomain.name in subdomain_names:
                raise ValueError(f"Duplicate subdomain name: {subdomain.name}")
            subdomain_names.add(subdomain.name)
        return self

class ApiKey(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    api_key: str = Field(description="Cloudflare API Key")
    account_email: str = Field(description="Cloudflare Account Email")

class Authentication(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    api_token: Optional[str] = Field(default=None, description="Cloudflare API Token")
    api_key: Optional[ApiKey] = Field(default=None, description="Cloudflare API Key configuration")

class CloudflareAccount(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    authentication: Authentication = Field(description="Authentication configuration")
    zones: List[Zone] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_unique_zones(self) -> 'CloudflareAccount':
        zone_ids = set()
        for zone in self.zones:
            if zone.zone_id in zone_ids:
                raise ValueError(f"Duplicate zone ID: {zone.zone_id}")
            zone_ids.add(zone.zone_id)
        return self

class Config(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    cloudflare: List[CloudflareAccount] = Field(default_factory=list)
    a: bool = Field(default=True, description="Enable A record updates")
    aaaa: bool = Field(default=True, description="Enable AAAA record updates")
    purgeUnknownRecords: bool = Field(default=False, description="Purge unknown DNS records")
    ttl: int = Field(default=300, ge=60, le=86400, description="Default TTL for DNS records")

def load_config() -> Config:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            data = json.load(f)
            # Ensure IDs exist for existing objects
            for account in data.get('cloudflare', []):
                if 'id' not in account:
                    account['id'] = str(uuid.uuid4())
                for zone in account.get('zones', []):
                    if 'id' not in zone:
                        zone['id'] = str(uuid.uuid4())
                    for subdomain in zone.get('subdomains', []):
                        if 'id' not in subdomain:
                            subdomain['id'] = str(uuid.uuid4())
            return Config.parse_obj(data)
    return Config()

def save_config(config: Config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.dict(), f, indent=2)

# Load initial config
config = load_config()

@app.get("/accounts", response_model=dict)
async def get_accounts():
    """
    Get all Cloudflare accounts
    """
    try:
        return create_response(
            error=False,
            data={"accounts": config.cloudflare},
            message="Accounts retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accounts", response_model=dict)
async def add_account(account: CloudflareAccount):
    """
    Add a new Cloudflare account.
    
    Note:
    - You can use either api_token or api_key, or both
    - For api_token, just provide the token string
    - For api_key, provide both api_key and account_email
    """
    try:
        # Check for duplicate authentication
        for existing_account in config.cloudflare:
            if (account.authentication.api_token and 
                account.authentication.api_token == existing_account.authentication.api_token):
                raise HTTPException(status_code=400, detail="API Token already exists")
            if (account.authentication.api_key and 
                account.authentication.api_key.api_key == existing_account.authentication.api_key.api_key):
                raise HTTPException(status_code=400, detail="API Key already exists")
            if (account.authentication.api_key and 
                account.authentication.api_key.account_email == existing_account.authentication.api_key.account_email):
                raise HTTPException(status_code=400, detail="Account email already exists")
        
        config.cloudflare.append(account)
        save_config(config)
        return create_response(
            error=False,
            data={"account": account},
            message="Account added successfully"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{account_id}", response_model=dict)
async def get_account(account_id: str):
    """
    Get a specific Cloudflare account by ID
    """
    try:
        for account in config.cloudflare:
            if account.id == account_id:
                return create_response(
                    error=False,
                    data={"account": account},
                    message="Account retrieved successfully"
                )
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/accounts/{account_id}", response_model=dict)
async def update_account(account_id: str, account: CloudflareAccount):
    """
    Update a specific Cloudflare account by ID
    """
    try:
        for i, existing_account in enumerate(config.cloudflare):
            if existing_account.id == account_id:
                account.id = account_id  # Ensure ID remains the same
                config.cloudflare[i] = account
                save_config(config)
                return create_response(
                    error=False,
                    data={"account": account},
                    message="Account updated successfully"
                )
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/accounts/{account_id}", response_model=dict)
async def delete_account(account_id: str):
    """
    Delete a specific Cloudflare account by ID
    """
    try:
        for i, account in enumerate(config.cloudflare):
            if account.id == account_id:
                config.cloudflare.pop(i)
                save_config(config)
                return create_response(
                    error=False,
                    message="Account deleted successfully"
                )
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/accounts/{account_id}/auth", response_model=dict)
async def update_authentication(account_id: str, auth: Authentication):
    """
    Update authentication for a specific account
    
    Note:
    - You can use either api_token or api_key, or both
    - For api_token, just provide the token string
    - For api_key, provide both api_key and account_email
    """
    try:
        for account in config.cloudflare:
            if account.id == account_id:
                account.authentication = auth
                save_config(config)
                return create_response(
                    error=False,
                    data={"auth": auth},
                    message="Authentication updated successfully"
                )
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts/{account_id}/zones", response_model=dict)
async def get_zones(account_id: str):
    """
    Get all zones for a specific account
    """
    try:
        for account in config.cloudflare:
            if account.id == account_id:
                return create_response(
                    error=False,
                    data={"zones": account.zones},
                    message="Zones retrieved successfully"
                )
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/accounts/{account_id}/zones", response_model=SuccessResponse)
async def create_zone(account_id: str, zone: ZoneCreate):
    """Create a new zone for an account"""
    try:
        # Get the account
        account = next((acc for acc in config.cloudflare if acc.id == account_id), None)
        if not account:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found")

        # Check if zone already exists
        if any(z for z in account.zones if z.zone_id == zone.zone_id):
            raise HTTPException(status_code=400, detail=f"Zone {zone.zone_id} already exists")

        # Create new zone
        new_zone = Zone(
            id=str(uuid.uuid4()),
            zone_id=zone.zone_id,
            domain=zone.domain,
            subdomains=[
                SubDomain(
                    id=str(uuid.uuid4()),
                    name=subdomain.name,
                    proxied=subdomain.proxied,
                    ttl=subdomain.ttl
                ) for subdomain in zone.subdomains
            ]
        )

        # Add zone to account
        account.zones.append(new_zone)
        save_config(config)

        return create_response(
            error=False,
            data={"zone": new_zone.model_dump()},
            message="Zone created successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/accounts/{account_id}/zones/{zone_id}", response_model=dict)
async def get_zone(account_id: str, zone_id: str):
    """
    Get a specific zone by ID
    """
    try:
        for account in config.cloudflare:
            if account.id == account_id:
                for zone in account.zones:
                    if zone.id == zone_id:
                        return create_response(
                            error=False,
                            data={"zone": zone},
                            message="Zone retrieved successfully"
                        )
                raise HTTPException(status_code=404, detail="Zone not found")
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/accounts/{account_id}/zones/{zone_id}", response_model=dict)
async def update_zone(account_id: str, zone_id: str, zone: Zone):
    """
    Update a specific zone by ID
    """
    try:
        for account in config.cloudflare:
            if account.id == account_id:
                for i, existing_zone in enumerate(account.zones):
                    if existing_zone.id == zone_id:
                        zone.id = zone_id  # Ensure ID remains the same
                        account.zones[i] = zone
                        save_config(config)
                        return create_response(
                            error=False,
                            data={"zone": zone},
                            message="Zone updated successfully"
                        )
                raise HTTPException(status_code=404, detail="Zone not found")
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/accounts/{account_id}/zones/{zone_id}", response_model=dict)
async def delete_zone(account_id: str, zone_id: str):
    """
    Delete a specific zone by ID
    """
    try:
        for account in config.cloudflare:
            if account.id == account_id:
                for i, zone in enumerate(account.zones):
                    if zone.id == zone_id:
                        account.zones.pop(i)
                        save_config(config)
                        return create_response(
                            error=False,
                            message="Zone deleted successfully"
                        )
                raise HTTPException(status_code=404, detail="Zone not found")
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
