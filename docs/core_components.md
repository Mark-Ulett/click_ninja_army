# Core Components Documentation

This document provides detailed information about each core component in the Click Ninja Army system.

## Data Transformer (`core/data_transformer.py`)

The Data Transformer is responsible for converting CSV input data into API-ready format.

### Key Responsibilities
- Validates input data structure and types
- Converts data types to required formats
- Parses category IDs from string format
- Transforms data into API-compatible format
- Handles error logging and reporting

### Usage Example
```python
from click_ninja_army.core.data_transformer import DataTransformer
import pandas as pd

df = pd.read_csv('input.csv')
transformer = DataTransformer()
transformed_data = transformer.transform_dataframe(df)
```

### Required Fields
- `campaign_id` (str): Campaign identifier
- `ad_item_id` (str): Ad item identifier
- `ad_tag` (str): Ad tag
- `ad_type` (str): Type of ad
- `ad_item_categories` (str): Category IDs

## Database Interface (`core/database.py`)

The Database Interface manages all database operations and request lifecycle.

### Key Responsibilities
- Manages SQLite database connections
- Handles CRUD operations for requests
- Tracks request status changes
- Logs operation history
- Provides data querying capabilities

### Usage Example
```python
from click_ninja_army.core.database import Database
from click_ninja_army.config.config import config

db = Database(config.db_path)

# Save new request
request_data = {
    'campaign_id': '123',
    'ad_item_id': '456',
    'status': 'pending'
}
db.save_ad_request(request_data)

# Update request status
db.update_request_status('request_123', 'completed')
```

### Database Schema
- `request_pool`: Stores request data
- `operation_log`: Tracks operation history

## Scout Ninja (`core/scout_ninja.py`)

The Scout Ninja handles parallel request generation with rate limiting and retry mechanisms.

### Key Responsibilities
- Generates ad requests in parallel
- Implements rate limiting per API endpoint
- Manages priority-based request queuing
- Handles automatic retry mechanism
- Tracks request generation progress
- Provides comprehensive error handling

### Usage Example
```python
from click_ninja_army.core.scout_ninja import ScoutNinja, RequestConfig
from click_ninja_army.config.config import config

# Configure request generation
request_config = RequestConfig(
    api_url='https://api.example.com',
    api_token='your_token',
    rate_limit=10,
    burst_limit=5
)

# Initialize Scout Ninja
scout = ScoutNinja(request_config, db, metrics_manager)

# Start request generation
scout.start()
scout.generate_requests(entries, priority=1)
```

### Configuration Options
- `rate_limit`: Requests per second
- `burst_limit`: Maximum burst size
- `max_retries`: Maximum retry attempts
- `retry_delay`: Delay between retries
- `timeout`: Request timeout

## Strike Ninja (`core/strike_ninja.py`)

The Strike Ninja handles parallel impression and click processing with separate worker pools and rate limiting.

### Key Responsibilities
- Processes impressions and clicks in parallel
- Manages separate worker pools for each operation type
- Implements rate limiting per operation
- Handles operation queuing
- Tracks success/failure metrics
- Provides performance metrics per ad item

### Usage Example
```python
from click_ninja_army.core.strike_ninja import StrikeNinja, OperationConfig, WorkerPoolConfig
from click_ninja_army.config.config import config

# Configure operation settings
operation_config = OperationConfig(
    impression_url='https://api.example.com/impression',
    click_url='https://api.example.com/click',
    api_token='your_token',
    impression_rate_limit=10,
    click_rate_limit=5,
    impression_burst=5,
    click_burst=3
)

# Initialize Strike Ninja
strike = StrikeNinja(operation_config, db, metrics_manager)

# Start processing
strike.start()
strike.queue_impression(entry, priority=1)
strike.queue_click(entry, priority=1)
```

### Configuration Options
- `impression_rate_limit`: Impressions per second
- `click_rate_limit`: Clicks per second
- `impression_burst`: Maximum impression burst
- `click_burst`: Maximum click burst
- `max_retries`: Maximum retry attempts
- `retry_delay`: Delay between retries

### Worker Pool Configuration
- Separate configurations for impression and click workers
- Configurable worker counts and queue sizes
- Automatic worker pool adjustment based on load
- Health monitoring and worker rotation

## Coordinator (`core/coordinator.py`)

The Coordinator orchestrates all system components.

### Key Responsibilities
- Manages component communication
- Coordinates workflow
- Handles system state
- Provides system coordination
- Manages error handling

### Usage Example
```python
from click_ninja_army.core.coordinator import Coordinator

coordinator = Coordinator()
coordinator.process_data(input_data)
```

### Workflow Management
1. Data validation
2. Request generation (impressions and clicks for each ad)
3. Task distribution
4. Execution monitoring
5. Result processing

## Component Interaction

The components interact in the following sequence:

1. **Data Flow**
   ```
   CSV Data → Data Transformer → Database → Request Generator (impressions & clicks) → Worker Pool → Scout/Strike → Results
   ```

2. **Status Flow**
   ```
   Request Status: pending → in_progress → completed/failed
   ```

3. **Error Flow**
   ```
   Error → Scout → Coordinator → Retry/Log
   ```

## Configuration

All configuration is centralized in `click_ninja_army/config/config.py`. **There is no .env or environment file.**
- Edit `config.py` to set API endpoints, tokens, database path, and other settings as needed.

## Best Practices

1. **Error Handling**
   - Use proper exception handling
   - Log errors with context
   - Implement retry mechanisms
   - Monitor error rates

2. **Performance**
   - Monitor resource usage
   - Implement rate limiting
   - Use connection pooling
   - Optimize database queries

3. **Maintenance**
   - Regular log rotation
   - Database cleanup
   - Performance monitoring
   - Error tracking

4. **Security**
   - Validate input data
   - Sanitize database queries
   - Secure API communication
   - Monitor access patterns