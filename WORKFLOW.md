# Click Ninja Army Workflow

## Overview
This document describes the complete workflow for the Click Ninja Army system, including all current functionality and data flows.

## Getting Started: Sequence Overview

1. **Prepare your campaign CSV file** (e.g., `input.csv`).
2. **Ingest and transform data:**
   ```bash
   python -m click_ninja_army.scripts.ingest_csv input.csv
   ```
3. **Generate ad requests (Scout Ninja):**
   ```bash
   python click_ninja_army/core/scout_ninja.py
   ```
4. **Process impressions and clicks (Strike Ninja):**
   ```bash
   python click_ninja_army/core/strike_ninja.py
   ```
5. **Monitor performance:**
   ```bash
   python click_ninja_army/core/monitoring.py
   ```

## System Components and Data Flow

### 1. Data Ingestion & Transformation
**Scripts Involved:**
- `click_ninja_army/scripts/ingest_csv.py`: Main entry point for CSV processing
- `click_ninja_army/core/data_transformer.py`: Handles data validation and transformation

**Database Tables:**
- `campaign_pool`:
  - `id` (INTEGER): Primary key, auto-incrementing
  - `ad_tag` (TEXT): Ad tag identifier, NOT NULL
  - `ad_item_id` (TEXT): Ad item identifier, NOT NULL
  - `creative_id` (INTEGER): Creative identifier, NOT NULL
  - `campaign_id` (TEXT): Campaign identifier, NOT NULL
  - `ad_type` (TEXT): Type of ad, NOT NULL
  - `keyword` (TEXT): Optional keyword
  - `category` (TEXT): Optional category
  - `created_at` (TIMESTAMP): Creation timestamp
  - Unique constraint on (ad_tag, ad_item_id, creative_id, campaign_id, ad_type, keyword, category)
  - Indexes:
    - `idx_campaign_pool_ad_item` on ad_item_id
    - `idx_campaign_pool_campaign` on campaign_id

**Process:**
1. CSV file validation
2. Field normalization
3. Data transformation
4. Campaign pool entry generation
5. Metrics logging

### 2. Campaign Pool Generation
**Scripts Involved:**
- `click_ninja_army/core/data_transformer.py`: Generates campaign pool entries
- `click_ninja_army/core/metrics.py`: Tracks generation metrics

**Database Tables:**
- `campaign_pool_metrics`:
  - `id` (INTEGER): Primary key, auto-incrementing
  - `csv_rows_processed` (INTEGER): Number of CSV rows processed
  - `campaign_pool_rows_generated` (INTEGER): Number of campaign pool entries generated
  - `generation_timestamp` (TIMESTAMP): Generation timestamp
  - `duration_seconds` (REAL): Generation duration
  - `status` (TEXT): Generation status

**Process:**
1. Base entry generation
2. Keyword/category combination generation
3. Metrics tracking
4. Database storage

### 3. Ad Request Generation (Scout Ninja)
**Scripts Involved:**
- `click_ninja_army/core/scout_ninja.py`: Handles request generation
- `click_ninja_army/core/monitoring.py`: Tracks performance metrics

**Database Tables:**
- `request_pool`:
  - `id` (INTEGER): Primary key, auto-incrementing
  - `campaign_pool_id` (INTEGER): Foreign key to campaign_pool
  - `ad_request_id` (TEXT): API-generated request ID
  - `request_timestamp` (TIMESTAMP): Request timestamp
  - `status` (TEXT): Request status (pending, in_progress, completed, failed)
  - Foreign key constraint on campaign_pool_id
  - Unique constraint on ad_request_id

- `request_pool_metrics`:
  - `id` (INTEGER): Primary key, auto-incrementing
  - `requests_generated` (INTEGER): Number of requests generated
  - `generation_timestamp` (TIMESTAMP): Generation timestamp
  - `duration_seconds` (REAL): Generation duration
  - `status` (TEXT): Generation status

**Process:**
1. Request generation
2. Rate limiting
3. Queue management
4. Metrics tracking

### 4. Impression & Click Processing (Strike Ninja)
**Scripts Involved:**
- `click_ninja_army/core/strike_ninja.py`: Handles impression and click processing
- `click_ninja_army/core/monitoring.py`: Tracks performance metrics

**Database Tables:**
- `operation_log`:
  - `id` (INTEGER): Primary key
  - `request_id` (TEXT): Request identifier
  - `operation_type` (TEXT): Operation type (impression/click)
  - `status` (TEXT): Operation status
  - `response_time` (FLOAT): API response time
  - `error_message` (TEXT): Error details if any
  - `created_at` (TIMESTAMP): Operation timestamp
  - Foreign key constraint on request_id

- `performance_metrics`:
  - `id` (INTEGER): Primary key
  - `ad_item_id` (TEXT): Ad item identifier
  - `operation_type` (TEXT): Type of operation
  - `success_count` (INTEGER): Number of successful operations
  - `failure_count` (INTEGER): Number of failed operations
  - `retry_count` (INTEGER): Number of retries
  - `avg_response_time` (REAL): Average response time
  - `total_operations` (INTEGER): Total number of operations
  - `last_updated` (TIMESTAMP): Last update timestamp
  - Unique constraint on (ad_item_id, operation_type)

### 5. Performance Monitoring

#### Centralized Metrics System
The system uses a distributed metrics tracking approach with centralized aggregation:

1. **MetricsManager (Core Component)**:
   - Central metrics collection and aggregation
   - Performance data storage and retrieval
   - Real-time metrics updates
   - Historical data tracking

2. **Component-Level Metrics**:
   - **DataTransformer Metrics**:
     - CSV rows processed
     - Campaign pool entries generated
     - Processing duration
     - Validation success/failure rates
   
   - **ScoutNinja Metrics**:
     - Requests generated
     - Request success/failure rates
     - API response times
     - Rate limit compliance
   
   - **StrikeNinja Metrics**:
     - Impression/click success rates
     - Operation response times
     - Retry counts
     - Worker pool utilization

3. **PerformanceMetrics Class**:
   - **Response Time Tracking**:
     - Per-ad-item response time history
     - Average response time calculation
     - Response time distribution analysis
   
   - **Operation Statistics**:
     - Success count per ad item
     - Failure count per ad item
     - Retry count tracking
     - Operation type breakdown
   
   - **Real-time Monitoring**:
     - Active operation tracking
     - Queue size monitoring
     - Worker pool health metrics
     - System resource utilization

4. **Metrics Storage**:
   - Database-backed metrics storage
   - Real-time metrics updates
   - Historical data retention
   - Metrics aggregation and reporting

### 6. Additional Monitoring Tables

- `monitoring_metrics`:
  - `id` (INTEGER): Primary key
  - `category` (TEXT): Metric category
  - `metric_name` (TEXT): Name of the metric
  - `metric_value` (REAL): Value of the metric
  - `timestamp` (TIMESTAMP): When the metric was recorded
  - Unique constraint on (category, metric_name, timestamp)

- `queue_metrics`:
  - `id` (INTEGER): Primary key
  - `queue_name` (TEXT): Name of the queue
  - `current_size` (INTEGER): Current queue size
  - `max_size` (INTEGER): Maximum queue size
  - `total_processed` (INTEGER): Total items processed
  - `avg_wait_time` (REAL): Average wait time
  - `timestamp` (TIMESTAMP): When the metric was recorded

- `worker_metrics`:
  - `id` (INTEGER): Primary key
  - `pool_name` (TEXT): Name of the worker pool
  - `active_workers` (INTEGER): Number of active workers
  - `total_tasks` (INTEGER): Total tasks processed
  - `avg_task_time` (REAL): Average task processing time
  - `utilization` (REAL): Worker pool utilization
  - `timestamp` (TIMESTAMP): When the metric was recorded

- `schema_version`:
  - `version` (INTEGER): Primary key, schema version number
  - `applied_at` (TIMESTAMP): When the version was applied
  - `description` (TEXT): Description of the version

## Worker Pool Management

### Worker Pool Rotation System
1. **Rotation Triggers and Process**:
   - **Task-Based Rotation**:
     - Workers are rotated after processing `max_tasks_per_worker` tasks
     - Rotation count is tracked per worker
     - New workers are initialized before old ones are shut down
     - Task queue is preserved during rotation
   
   - **Idle-Based Rotation**:
     - Workers are removed after `idle_timeout` seconds of inactivity
     - Idle time is tracked per worker
     - Active task count is monitored
     - Resources are reclaimed after rotation

2. **Health Check Implementation**:
   - **Periodic Health Monitoring**:
     - Health checks run every 10 seconds
     - Worker activity is tracked in real-time
     - Response times are monitored
     - Error rates are calculated
   
   - **Worker Pool Adjustment**:
     - Pool size is adjusted based on load
     - New workers are added when needed
     - Idle workers are removed
     - Resources are reallocated

3. **Resource Management**:
   - **Worker Lifecycle**:
     - Initialization with configured parameters
     - Task processing with rate limiting
     - Health monitoring and adjustment
     - Graceful shutdown
   
   - **Resource Optimization**:
     - Dynamic worker count adjustment
     - Queue size management
     - Memory usage monitoring
     - CPU utilization tracking

### Priority Queuing System
1. **Queue Implementation**:
   - **Priority Levels**:
     - Higher priority (lower number) tasks are processed first
     - Default priority is 0
     - Negative priorities for urgent tasks
     - Positive priorities for background tasks
   
   - **Queue Management**:
     - Thread-safe priority queue implementation
     - Configurable queue sizes per worker pool
     - Queue overflow handling
     - Task prioritization rules

2. **Task Scheduling**:
   - **Priority Rules**:
     - Impression tasks: Priority 0-2
     - Click tasks: Priority 0-1
     - Background tasks: Priority 3+
     - System tasks: Priority -1
   
   - **Scheduling Algorithm**:
     - Priority-based task selection
     - Fair queuing within priority levels
     - Rate limit consideration
     - Resource availability check

## Category ID Processing

### Category ID Format and Parsing
1. **Input Format**:
   - Category IDs are provided in the format: `"{1019,1007,1006}"`
   - Curly braces `{}` are required
   - Comma-separated integer values
   - No spaces between numbers
   - Example: `"{1019,1007,1006}"`

2. **Parsing Process**:
   - **Validation Steps**:
     - Check for valid string format
     - Validate curly brace presence
     - Parse comma-separated values
     - Convert to integers
   
   - **Error Handling**:
     - Invalid format detection
     - Non-numeric value handling
     - Empty category handling
     - Malformed input recovery

3. **Output Format**:
   - List of integer category IDs
   - Sorted for consistency
   - Duplicates removed
   - Empty list for invalid input

## Critical Requirements

### adRequestId Validation
1. **Generation Requirements**:
   - Must be generated by the backend API only
   - Never generated by the client or input data
   - Must be unique across all requests
   - Must follow the format: `uuid/suffix`

2. **Validation Rules**:
   - **Format Validation**:
     - Must contain exactly one forward slash
     - UUID part must be at least 8 characters
     - Suffix must be present and valid
     - No special characters allowed in suffix
   
   - **Content Validation**:
     - UUID part must be alphanumeric
     - Suffix must be alphanumeric with allowed special characters (-_)
     - No whitespace allowed
     - Case-sensitive matching

3. **Implementation Details**:
   - Validation occurs at multiple points:
     - During request generation
     - Before impression processing
     - Before click processing
     - During database operations

4. **Error Handling**:
   - Invalid IDs are rejected immediately
   - Detailed error messages are logged
   - Failed validations are tracked
   - Recovery procedures are implemented

## Success Criteria
1. All combinations correctly generated in campaign pool
2. Parallel processing working efficiently
3. Rate limiting properly enforced
4. Metrics accurately tracked
5. Error handling robust
6. Performance meets requirements

## Monitoring and Metrics

- **MetricsManager** uses the `performance_metrics` table to track per-ad-item, per-operation metrics (e.g., success counts, response times).
- **MonitoringSystem** uses a separate table named `monitoring_metrics` to track general category/metric/time-based metrics, avoiding collisions with MetricsManager.

## Error Handling and System Reliability

### Circuit Breaker and Global Failure Counter
- Both Scout Ninja and Strike Ninja now include a global failure counter and circuit breaker logic.
- If a threshold of consecutive API failures (e.g., 20) is reached, the system will pause all workers for a cooldown period (default: 60 seconds).
- After the cooldown, the system resumes processing and continues to monitor for further errors.
- This prevents endless worker spawning and API hammering during persistent backend errors or misconfiguration, ensuring system stability and resource efficiency.
- All circuit breaker events and resumptions are logged for monitoring and debugging.