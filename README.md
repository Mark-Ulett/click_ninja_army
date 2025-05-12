# Click Ninja Army

A streamlined system for processing ad server data and generating ad requests. The system focuses on simplicity and efficiency, using SQLite for data storage and a straightforward processing pipeline.

## System Architecture

### Core Components

1. **Data Transformer** (`core/data_transformer.py`)
   - Processes CSV input data
   - Validates required fields and data types
   - Transforms data into API-ready format
   - Handles category ID parsing and validation

2. **Database Interface** (`core/database.py`)
   - SQLite-based storage system
   - Manages request lifecycle
   - Tracks operation history
   - Provides CRUD operations
   - Handles table creation and indexing

3. **Request Generator** (`core/request_generator.py`)
   - Generates API-compatible requests
   - Supports multiple ad types
   - Handles request formatting
   - Manages API communication
   - Processes responses

4. **Worker Pool** (`core/worker_pool.py`)
   - Manages concurrent processing
   - Handles task distribution
   - Controls resource utilization
   - Provides worker lifecycle management
   - Implements error handling

5. **Scout** (`core/scout.py`)
   - Monitors system performance
   - Tracks request metrics
   - Provides real-time insights
   - Manages system health

6. **Strike** (`core/strike.py`)
   - Executes ad requests
   - Handles retry logic
   - Manages error recovery
   - Tracks execution status

7. **Coordinator** (`core/coordinator.py`)
   - Orchestrates system components
   - Manages workflow
   - Handles component communication
   - Provides system coordination

### Data Flow

The system processes data through several well-defined stages, each handled by specific components:

1. **Input Processing** (`core/data_transformer.py`)
   ```
   CSV File → Data Transformer → Validated Data
   ```
   - CSV file is read using pandas
   - Data Transformer validates required fields:
     - campaign_id (str)
     - ad_item_id (str)
     - ad_tag (str)
     - ad_type (str)
     - ad_item_categories (str)
   - Category IDs are parsed from string format
   - Data is transformed into API-ready format
   - Invalid rows are logged and excluded

2. **Database Storage** (`core/database.py`)
   ```
   Validated Data → Database → Request Pool
   ```
   - SQLite database is initialized with tables:
     - request_pool: Stores ad requests and status
     - operation_log: Tracks operation history
   - Each request is stored with:
     - Unique request_id
     - Campaign details
     - Ad specifications
     - Status (pending/in_progress/completed/failed)
     - Priority and retry count
   - Indexes are created for efficient querying

3. **Request Generation** (`core/request_generator.py`)
   ```
   Database → Request Generator → API Requests
   ```
   - Request Generator creates API-compatible payloads:
     - Adds authentication headers
     - Formats request data
     - Handles different ad types (Display/Video)
     - Manages API communication
   - Rate limiting is applied (configurable)
   - Responses are processed and validated

4. **Execution Pipeline** (`core/coordinator.py`, `core/scout.py`, `core/strike.py`)
   ```
   API Requests → Worker Pool → Scout/Strike → Results
   ```
   - Coordinator orchestrates the workflow:
     - Initializes Scout and Strike Ninjas
     - Manages component communication
     - Handles error recovery
   - Scout Ninja:
     - Monitors system performance
     - Tracks request metrics
     - Manages request queue
   - Strike Ninja:
     - Executes ad operations
     - Handles retry logic
     - Tracks execution status

5. **Status Tracking** (`core/database.py`)
   ```
   Results → Database → Operation Log
   ```
   - Operation results are logged:
     - Success/failure status
     - Response times
     - Error messages
     - Timestamps
   - Request status is updated
   - Performance metrics are recorded

6. **Worker Management** (`core/worker_pool.py`)
   ```
   Tasks → Worker Pool → Processed Results
   ```
   - Worker Pool manages concurrent processing:
     - Creates and manages worker threads
     - Distributes tasks from queue
     - Handles task results
     - Implements error handling
   - Resource utilization is controlled
   - Graceful shutdown is supported

7. **Performance Monitoring** (`core/scout.py`)
   ```
   System → Scout → Metrics
   ```
   - Real-time metrics collection:
     - Request success rate
     - Processing time
     - Error rates
     - Resource utilization
   - Performance alerts
   - System health monitoring

Each stage in the pipeline is designed to be:
- Independent and modular
- Error-resistant with proper logging
- Performance-optimized
- Easily monitored and debugged

The data flow is managed by the Coordinator (`core/coordinator.py`), which ensures:
- Proper sequencing of operations
- Error handling and recovery
- Resource management
- System state consistency

### Configuration

All configuration is centralized in `click_ninja_army/config/config.py`. **There is no .env or environment file.**
- Edit `config.py` to set API endpoints, tokens, database path, and other settings as needed.
- See `summary_of_config.md` for detailed configuration options.

### Installation

1. **Prerequisites**
   - Python 3.8 or higher
   - pip (Python package manager)
   - virtualenv or venv

2. **Setup**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   source venv/bin/activate  # On Unix/macOS
   # or
   .\venv\Scripts\activate  # On Windows
   
   # Install dependencies
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

```python
from click_ninja_army.core.data_transformer import DataTransformer
from click_ninja_army.core.database import Database
from click_ninja_army.core.request_generator import RequestGenerator
from click_ninja_army.config.config import config

# Initialize components
transformer = DataTransformer()
db = Database(config.db_path)
generator = RequestGenerator(config)

# Process data
import pandas as pd
df = pd.read_csv('input.csv')
transformed_data = transformer.transform_dataframe(df)

# Save to database
for row in transformed_data.to_dict(orient='records'):
    db.save_ad_request(row)

# Generate both impressions and clicks for each ad
for row in transformed_data.to_dict(orient='records'):
    for op_type in ['impression', 'click']:
        row['operation_type'] = op_type
        generator.generate_request(row)
```

### Main Script Usage

You can also use the provided `run_click_ninja.py` script, which will:
- Load and transform your CSV
- Save requests to the database
- For each ad, generate both an impression and a click

```bash
python run_click_ninja.py
```

## Development

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Write comprehensive docstrings
- Include unit tests

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=click_ninja_army
```

### Database Management
```bash
# View database schema
sqlite3 click_ninja.db ".schema"

# Query requests
sqlite3 click_ninja.db "SELECT * FROM request_pool WHERE status = 'pending';"

# View operation log
sqlite3 click_ninja.db "SELECT * FROM operation_log ORDER BY created_at DESC LIMIT 10;"
```

## Monitoring

### Performance Metrics
- Request success rate
- Processing time
- Error rates
- Resource utilization

### Logging
- Request/response logging
- Error tracking
- Performance metrics
- System events

## Troubleshooting

### Common Issues
1. **Database Connection**
   - Verify database exists
   - Check permissions
   - Validate schema

2. **API Issues**
   - Check API token in `config.py`
   - Verify endpoints in `config.py`
   - Monitor rate limits

3. **Performance Issues**
   - Check worker configuration
   - Monitor resource usage
   - Review rate limits

## Support

For support:
1. Check the documentation
2. Review existing issues
3. Submit new issues with:
   - Detailed description
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment details

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Authors

- Your Name - Initial work and maintenance 