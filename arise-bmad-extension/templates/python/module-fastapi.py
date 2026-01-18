"""
{{MODULE_NAME}}
{{DESCRIPTION}}

Implements AsyncAPI specification: asyncapi.yaml
Uses CloudEvents v1.0 format

Part of Arise modular integration platform.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone
import yaml
import json
import re

# Optional: CloudEvents SDK
try:
    from cloudevents.http import CloudEvent, to_structured, from_http
    CLOUDEVENTS_SDK = True
except ImportError:
    CLOUDEVENTS_SDK = False

# Optional: JSON Schema validation
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False


# =============================================================================
# Configuration
# =============================================================================

MODULE_ID = "{{MODULE_ID}}"
MODULE_VERSION = "{{VERSION}}"
MODULE_TYPE = "{{MODULE_TYPE}}"

# Event types
INPUT_EVENT_TYPE = "{{INPUT_EVENT_TYPE}}"
OUTPUT_EVENT_TYPE = "{{OUTPUT_EVENT_TYPE}}"

# Load AsyncAPI specification
try:
    with open('asyncapi.yaml', 'r') as f:
        ASYNCAPI_SPEC = yaml.safe_load(f)
except FileNotFoundError:
    ASYNCAPI_SPEC = None
    print("Warning: asyncapi.yaml not found")


# =============================================================================
# Pydantic Models
# =============================================================================

class CloudEventModel(BaseModel):
    """CloudEvents v1.0 message model"""
    specversion: str = Field("1.0", description="CloudEvents version")
    type: str = Field(..., description="Event type identifier")
    source: str = Field(..., description="Event source")
    id: str = Field(..., description="Unique event ID")
    time: Optional[str] = Field(None, description="Event timestamp")
    datacontenttype: str = Field("application/json", description="Data content type")
    data: Dict[str, Any] = Field(..., description="Event payload")
    correlationid: Optional[str] = Field(None, description="Correlation ID for tracing")

    @field_validator('specversion')
    @classmethod
    def validate_version(cls, v):
        if v != "1.0":
            raise ValueError('CloudEvents version must be 1.0')
        return v

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        pattern = r'^com\.arise\.[a-z]+\.[a-z]+\.[a-z]+\.v[0-9]+$'
        if not re.match(pattern, v):
            raise ValueError('Event type must follow pattern: com.arise.<domain>.<entity>.<action>.v<version>')
        return v


# Define your data models based on AsyncAPI spec
class InputData(BaseModel):
    """Input data model - customize based on your AsyncAPI spec"""
    # Example fields - replace with your actual schema
    # sensorId: str
    # value: float
    # timestamp: Optional[str] = None
    pass


class OutputData(BaseModel):
    """Output data model - customize based on your AsyncAPI spec"""
    # Example fields - replace with your actual schema
    # sensorId: str
    # value: float
    # processed: bool
    # processedAt: str
    pass


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title=MODULE_ID,
    description=f"{{DESCRIPTION}}",
    version=MODULE_VERSION
)


@app.post("/process")
async def process_event(event: CloudEventModel):
    """
    Main processing endpoint.
    Accepts CloudEvents messages, validates against AsyncAPI spec, processes data.
    """

    # Validate CloudEvents format
    if event.specversion != "1.0":
        raise HTTPException(status_code=400, detail="Invalid CloudEvents version")

    # Validate event type (optional: check against expected input type)
    # if event.type != INPUT_EVENT_TYPE:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Invalid event type. Expected: {INPUT_EVENT_TYPE}"
    #     )

    # Validate data against AsyncAPI schema (if available)
    if ASYNCAPI_SPEC and JSONSCHEMA_AVAILABLE:
        try:
            validate_against_asyncapi_schema(event.data)
        except jsonschema.ValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Schema validation failed: {e.message}"
            )

    # Process data (implement your business logic)
    try:
        result = process_data(event.data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Processing error: {str(e)}"
        )

    # Create response CloudEvent
    response_event = create_response_event(result, event.id)

    return response_event


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "module_id": MODULE_ID,
        "version": MODULE_VERSION,
        "type": MODULE_TYPE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "asyncapi_loaded": ASYNCAPI_SPEC is not None
    }


@app.get("/manifest")
async def get_manifest():
    """Return module manifest"""
    try:
        with open('manifest.yaml', 'r') as f:
            manifest = yaml.safe_load(f)
        return manifest
    except FileNotFoundError:
        return {
            "module": {
                "id": MODULE_ID,
                "version": MODULE_VERSION,
                "type": MODULE_TYPE
            }
        }


@app.get("/schema")
async def get_schema():
    """Return AsyncAPI specification"""
    if ASYNCAPI_SPEC:
        return ASYNCAPI_SPEC
    raise HTTPException(status_code=404, detail="AsyncAPI spec not found")


# =============================================================================
# Business Logic
# =============================================================================

def validate_against_asyncapi_schema(data: Dict[str, Any]) -> None:
    """
    Validate data payload against AsyncAPI message schema.
    Raises jsonschema.ValidationError if invalid.
    """
    if not ASYNCAPI_SPEC or not JSONSCHEMA_AVAILABLE:
        return

    # Navigate to the input data schema in AsyncAPI spec
    # Adjust path based on your actual spec structure
    try:
        schemas = ASYNCAPI_SPEC.get('components', {}).get('schemas', {})
        # Find the input data schema (customize this path)
        schema = schemas.get('InputData') or schemas.get('{{INPUT_DATA_SCHEMA_NAME}}')
        if schema:
            jsonschema.validate(instance=data, schema=schema)
    except KeyError:
        pass  # Schema not found, skip validation


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Your module's business logic.

    Args:
        data: Input data from CloudEvents message

    Returns:
        Processed data dictionary
    """
    # ==========================================================
    # TODO: Implement your processing logic here
    # ==========================================================
    #
    # Example for a validator module:
    # is_valid = all(field in data for field in ['sensorId', 'value'])
    # return {
    #     **data,
    #     'validationStatus': 'valid' if is_valid else 'invalid',
    #     'validatedAt': datetime.now(timezone.utc).isoformat()
    # }
    #
    # Example for an enricher module:
    # context = load_context(data.get('sensorId'))
    # return {
    #     **data,
    #     'location': context.get('location'),
    #     'deviceType': context.get('deviceType')
    # }
    #
    # Example for a processor module:
    # threshold = 70.0
    # return {
    #     **data,
    #     'alertTriggered': data.get('value', 0) > threshold,
    #     'processedAt': datetime.now(timezone.utc).isoformat()
    # }

    result = {
        **data,
        "processed": True,
        "processedAt": datetime.now(timezone.utc).isoformat(),
        "processedBy": MODULE_ID
    }

    return result


def create_response_event(data: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """
    Create CloudEvents response message.

    Args:
        data: Processed data
        correlation_id: Original event ID for correlation

    Returns:
        CloudEvents formatted response
    """
    event = {
        "specversion": "1.0",
        "type": OUTPUT_EVENT_TYPE,
        "source": MODULE_ID,
        "id": str(uuid.uuid4()),
        "time": datetime.now(timezone.utc).isoformat(),
        "datacontenttype": "application/json",
        "data": data,
        "correlationid": correlation_id  # Extension attribute for tracing
    }

    return event


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port={{PORT}})
