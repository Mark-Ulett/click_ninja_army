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

## Request Generator (`core/request_generator.py`)

The Request Generator creates API-compatible requests from validated data.

### Key Responsibilities
- Generates API request payloads
- Handles different ad types
- Manages request formatting
- Validates request structure
- Handles API communication

### Usage Example
```python
from click_ninja_army.core.request_generator import RequestGenerator
from click_ninja_army.config.config import config

generator = RequestGenerator(config)

# Generate both impressions and clicks for each ad
row = {
    'adTag': 'example-tag',
    'adItemId': 123,
    'adType': 'Display',
    'campaign_id': 'camp_001',
    # ... other required fields ...
}
for op_type in ['impression', 'click']:
    row['operation_type'] = op_type
    generator.generate_request(row)
```

### Supported Ad Types
- Display
- Video
- Native (Fixed/Dynamic)
- Product

## Worker Pool (`core/worker_pool.py`)

The Worker Pool manages concurrent processing of requests.

### Key Responsibilities
- Manages worker threads
- Distributes tasks
- Controls resource usage
- Handles worker lifecycle
- Provides task queuing

### Usage Example
```python
from click_ninja_army.core.worker_pool import WorkerPool

pool = WorkerPool(max_workers=10)

# Submit task
pool.submit_task(task_function, task_data)
```

### Configuration Options
- `max_workers`: Maximum number of worker threads
- `queue_size`: Maximum task queue size
- `timeout`: Task timeout in seconds

## Scout (`core/scout.py`)

The Scout monitors system performance and health.

### Key Responsibilities
- Tracks request metrics
- Monitors system performance
- Provides real-time insights
- Manages system health
- Generates performance reports

### Usage Example
```python
from click_ninja_army.core.scout import Scout

scout = Scout(metrics_interval=60)
scout.start_monitoring()
```

### Monitored Metrics
- Request success rate
- Processing time
- Error rates
- Resource utilization

## Strike (`core/strike.py`)

The Strike executes ad requests and handles retries.

### Key Responsibilities
- Executes API requests
- Manages retry logic
- Handles error recovery
- Tracks execution status
- Provides execution reports

### Usage Example
```python
from click_ninja_army.core.strike import Strike

strike = Strike(max_retries=3)
result = strike.execute_request(request_data)
```

### Configuration Options
- `max_retries`: Maximum retry attempts
- `retry_delay`: Delay between retries
- `timeout`: Request timeout

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
```