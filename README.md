# Click Ninja Army

## Overview
Click Ninja Army is a modular, parallelized system for managing ad campaign requests, impressions, and clicks. It features robust data ingestion, campaign pool generation, request queuing, rate limiting, and performance monitoring, all backed by a structured SQLite database.

## Features
- CSV-based campaign ingestion and transformation
- Campaign pool generation with keyword/category expansion
- Parallel ad request generation (Scout Ninja)
- Parallel impression and click processing (Strike Ninja)
- Rate limiting and queue management
- Centralized performance monitoring and metrics
- Extensible worker pool configuration
- **Robust error handling with circuit breaker:** If repeated API failures occur, the system will pause all workers for a cooldown period and then resume, preventing endless worker spawning and API hammering.

## System Architecture
- **Data Ingestion & Transformation:** Validates and normalizes CSVs, generates campaign pool entries
- **Campaign Pool Generation:** Expands base entries with keyword/category combinations, tracks metrics
- **Ad Request Generation (Scout Ninja):** Handles parallel request generation, rate limiting, and queuing
- **Impression & Click Processing (Strike Ninja):** Processes impressions/clicks in parallel, logs operations and metrics
- **Performance Monitoring:** Tracks system health, queue sizes, worker utilization, and error rates
- **Database Management:** Handles schema migrations, versioning, and backups
- **Circuit Breaker for API Errors:** If a threshold of consecutive failures is reached, all workers are paused for a cooldown period before resuming, ensuring system stability during backend outages or misconfiguration.

## Project Structure
```
Click_Ninja_Army_1.1/
├── click_ninja_army/
│   ├── core/           # Core system components
│   ├── scripts/        # Command-line scripts
│   ├── tests/          # Test suite
│   ├── config/         # Configuration files
│   └── __init__.py
├── docs/               # Documentation
├── logs/              # System logs
├── APIs/              # API integration files
├── click_ninja.db     # Main database
├── requirements.txt   # Python dependencies
└── README.md
```

## Database Schema
### Core Tables
- `campaign_pool`: Stores all campaign/ad/creative combinations with metrics
- `campaign_pool_metrics`: Tracks campaign pool generation statistics
- `request_pool`: Stores ad requests and their statuses
- `operation_log`: Logs impressions/clicks and their outcomes
- `performance_metrics`: Centralized metrics for system health

### Monitoring Tables
- `monitoring_metrics`: System-wide monitoring data
- `queue_metrics`: Queue performance and status
- `worker_metrics`: Worker pool utilization and performance
- `schema_version`: Database schema version tracking

## Setup
1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd Click_Ninja_Army_1.1
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Initialize the database:**
   ```bash
   python click_ninja_army/core/database_migration.py
   ```
4. **Configure worker pools and operation settings:**
   - Edit your configuration file or environment variables as needed (see `WORKFLOW.md` for details)

## Usage
- **Ingest a new campaign CSV:**
  ```bash
  python -m click_ninja_army.scripts.ingest_csv <input.csv>
  ```
- **Generate ad requests:**
  ```bash
  python click_ninja_army/core/scout_ninja.py
  ```
- **Process impressions/clicks:**
  ```bash
  python click_ninja_army/core/strike_ninja.py
  ```
- **Monitor performance:**
  ```bash
  python click_ninja_army/core/monitoring.py
  ```

## ScoutNinja Runner
The ScoutNinja module includes a dedicated runner script (`run_scout_ninja.py`) that provides a command-line interface for testing and running the ScoutNinja module. The script includes proper error handling and logging.

### Usage Examples
```bash
# Test the parser component
python run_scout_ninja.py --test-parser --input-file path/to/your/input.csv

# Test the validator component
python run_scout_ninja.py --test-validator --input-file path/to/your/input.csv

# Test the processor component
python run_scout_ninja.py --test-processor --input-file path/to/your/input.csv

# Run the full workflow
python run_scout_ninja.py --input-file path/to/your/input.csv

# Use custom config and debug logging
python run_scout_ninja.py --input-file path/to/your/input.csv --config-file custom_config.yaml --log-level DEBUG
```

### Features
- **Component Testing**: Test individual components (parser, validator, processor) separately
- **Full Workflow Testing**: Run the complete ScoutNinja workflow
- **Configuration Flexibility**: Customize config file location and logging level
- **Error Handling**: Comprehensive error handling and logging

### Benefits
- Debug each component independently
- Verify the data flow between components
- Test the full workflow when ready
- Have a clear entry point for the ScoutNinja module

## Contribution Guidelines
- Please review `WORKFLOW.md` for system details and architecture.
- Ensure all new scripts and functions include clear docstrings and type annotations.
- Update or add tests for new features.
- Keep documentation up to date with any changes.

## Critical Requirements
- `adRequestId` is always generated by the backend API (never in the CSV)
- Impressions/clicks must use the exact `adRequestId` from the request phase
- System must enforce rate limits and parallelism as configured
- All database operations must maintain referential integrity
- Performance metrics must be tracked for all operations

## ScoutNinja Runner Implementation

### Overview
The ScoutNinja module now includes a dedicated runner script (`run_scout_ninja.py`) that provides a command-line interface for testing and running the ScoutNinja module. The script includes proper error handling and logging.

### Usage Examples
```bash
# Test the parser component
python run_scout_ninja.py --test-parser --input-file path/to/your/input.csv

# Test the validator component
python run_scout_ninja.py --test-validator --input-file path/to/your/input.csv

# Test the processor component
python run_scout_ninja.py --test-processor --input-file path/to/your/input.csv

# Run the full workflow
python run_scout_ninja.py --input-file path/to/your/input.csv

# Use custom config and debug logging
python run_scout_ninja.py --input-file path/to/your/input.csv --config-file custom_config.yaml --log-level DEBUG
```

### Features
- **Component Testing**: Test individual components (parser, validator, processor) separately
- **Full Workflow Testing**: Run the complete ScoutNinja workflow
- **Configuration Flexibility**: Customize config file location and logging level
- **Error Handling**: Comprehensive error handling and logging

### Benefits
- Debug each component independently
- Verify the data flow between components
- Test the full workflow when ready
- Have a clear entry point for the ScoutNinja module

*Note: This document should be reviewed and updated as new issues are discovered or existing ones are resolved.* 
## Contact
Mark Ulett
