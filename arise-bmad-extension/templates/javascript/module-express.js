/**
 * {{MODULE_NAME}}
 * {{DESCRIPTION}}
 *
 * Implements AsyncAPI specification: asyncapi.yaml
 * Uses CloudEvents v1.0 format
 *
 * Part of Arise modular integration platform.
 */

const express = require('express');
const Ajv = require('ajv');
const addFormats = require('ajv-formats');
const yaml = require('js-yaml');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

// Optional: CloudEvents SDK
let CloudEvents;
try {
  CloudEvents = require('cloudevents');
} catch (e) {
  CloudEvents = null;
}

const app = express();
app.use(express.json());

// =============================================================================
// Configuration
// =============================================================================

const MODULE_ID = '{{MODULE_ID}}';
const MODULE_VERSION = '{{VERSION}}';
const MODULE_TYPE = '{{MODULE_TYPE}}';
const PORT = process.env.PORT || {{PORT}};

// Event types
const INPUT_EVENT_TYPE = '{{INPUT_EVENT_TYPE}}';
const OUTPUT_EVENT_TYPE = '{{OUTPUT_EVENT_TYPE}}';

// Load AsyncAPI specification
let asyncapiSpec = null;
try {
  asyncapiSpec = yaml.load(fs.readFileSync('asyncapi.yaml', 'utf8'));
} catch (e) {
  console.warn('Warning: asyncapi.yaml not found');
}

// JSON Schema validator
const ajv = new Ajv({ allErrors: true });
addFormats(ajv);

// =============================================================================
// Endpoints
// =============================================================================

/**
 * Main processing endpoint
 * POST /process
 */
app.post('/process', async (req, res) => {
  try {
    const event = req.body;

    // Validate CloudEvents format
    validateCloudEvent(event);

    // Validate data against AsyncAPI schema
    if (asyncapiSpec) {
      validateAgainstAsyncAPI(event.data);
    }

    // Process data
    const result = await processData(event.data);

    // Create response CloudEvent
    const responseEvent = createResponseEvent(result, event.id);

    // Send response
    res.status(200)
      .set('Content-Type', 'application/cloudevents+json')
      .json(responseEvent);

  } catch (error) {
    console.error('Processing error:', error);

    const errorResponse = createErrorEvent(error);
    res.status(error.statusCode || 500)
      .set('Content-Type', 'application/cloudevents+json')
      .json(errorResponse);
  }
});

/**
 * Health check endpoint
 * GET /health
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    module_id: MODULE_ID,
    version: MODULE_VERSION,
    type: MODULE_TYPE,
    timestamp: new Date().toISOString(),
    asyncapi_loaded: asyncapiSpec !== null
  });
});

/**
 * Get module manifest
 * GET /manifest
 */
app.get('/manifest', (req, res) => {
  try {
    const manifest = yaml.load(fs.readFileSync('manifest.yaml', 'utf8'));
    res.json(manifest);
  } catch (e) {
    res.json({
      module: {
        id: MODULE_ID,
        version: MODULE_VERSION,
        type: MODULE_TYPE
      }
    });
  }
});

/**
 * Get AsyncAPI specification
 * GET /schema
 */
app.get('/schema', (req, res) => {
  if (asyncapiSpec) {
    res.json(asyncapiSpec);
  } else {
    res.status(404).json({ error: 'AsyncAPI spec not found' });
  }
});

// =============================================================================
// Validation Functions
// =============================================================================

/**
 * Validate CloudEvents format
 */
function validateCloudEvent(event) {
  // Check specversion
  if (!event.specversion || event.specversion !== '1.0') {
    const error = new Error('Invalid CloudEvents version. Expected 1.0');
    error.statusCode = 400;
    throw error;
  }

  // Check required fields
  if (!event.type || !event.source || !event.id) {
    const error = new Error('Missing required CloudEvents fields (type, source, id)');
    error.statusCode = 400;
    throw error;
  }

  // Validate event type pattern
  const typePattern = /^com\.arise\.[a-z]+\.[a-z]+\.[a-z]+\.v[0-9]+$/;
  if (!typePattern.test(event.type)) {
    const error = new Error('Invalid event type format. Expected: com.arise.<domain>.<entity>.<action>.v<version>');
    error.statusCode = 400;
    throw error;
  }

  // Check data field
  if (event.data === undefined) {
    const error = new Error('Missing required CloudEvents field: data');
    error.statusCode = 400;
    throw error;
  }
}

/**
 * Validate data against AsyncAPI schema
 */
function validateAgainstAsyncAPI(data) {
  if (!asyncapiSpec) return;

  // Navigate to the input data schema
  // Adjust path based on your actual spec structure
  const schemas = asyncapiSpec.components?.schemas || {};
  const schema = schemas.InputData || schemas['{{INPUT_DATA_SCHEMA_NAME}}'];

  if (schema) {
    const validate = ajv.compile(schema);
    const valid = validate(data);

    if (!valid) {
      const error = new Error(`Schema validation failed: ${ajv.errorsText(validate.errors)}`);
      error.statusCode = 400;
      error.validationErrors = validate.errors;
      throw error;
    }
  }
}

// =============================================================================
// Business Logic
// =============================================================================

/**
 * Your module's business logic
 *
 * @param {Object} data - Input data from CloudEvents message
 * @returns {Object} - Processed data
 */
async function processData(data) {
  // ==========================================================
  // TODO: Implement your processing logic here
  // ==========================================================
  //
  // Example for a validator module:
  // const isValid = data.sensorId && data.value !== undefined;
  // return {
  //   ...data,
  //   validationStatus: isValid ? 'valid' : 'invalid',
  //   validatedAt: new Date().toISOString()
  // };
  //
  // Example for an enricher module:
  // const context = await loadContext(data.sensorId);
  // return {
  //   ...data,
  //   location: context.location,
  //   deviceType: context.deviceType
  // };
  //
  // Example for a processor module:
  // const threshold = 70.0;
  // return {
  //   ...data,
  //   alertTriggered: (data.value || 0) > threshold,
  //   processedAt: new Date().toISOString()
  // };

  const result = {
    ...data,
    processed: true,
    processedAt: new Date().toISOString(),
    processedBy: MODULE_ID
  };

  return result;
}

// =============================================================================
// Response Helpers
// =============================================================================

/**
 * Create CloudEvents response message
 */
function createResponseEvent(data, correlationId) {
  return {
    specversion: '1.0',
    type: OUTPUT_EVENT_TYPE,
    source: MODULE_ID,
    id: uuidv4(),
    time: new Date().toISOString(),
    datacontenttype: 'application/json',
    data: data,
    correlationid: correlationId  // Extension attribute for tracing
  };
}

/**
 * Create error response in CloudEvents format
 */
function createErrorEvent(error) {
  return {
    specversion: '1.0',
    type: `com.arise.${MODULE_TYPE}.error.v1`,
    source: MODULE_ID,
    id: uuidv4(),
    time: new Date().toISOString(),
    datacontenttype: 'application/json',
    data: {
      error: true,
      message: error.message,
      module: MODULE_ID,
      timestamp: new Date().toISOString()
    }
  };
}

// =============================================================================
// Start Server
// =============================================================================

app.listen(PORT, () => {
  console.log(`${MODULE_ID} v${MODULE_VERSION} listening on port ${PORT}`);
  if (asyncapiSpec) {
    console.log(`AsyncAPI spec: ${asyncapiSpec.info?.title} v${asyncapiSpec.info?.version}`);
  }
});

// Export for testing
module.exports = app;
