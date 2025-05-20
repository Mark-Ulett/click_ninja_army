# Step-by-Step Instructions for Click Ninja Army

## Prerequisites

1. **Python Environment**
   - Python 3.8 or higher
   - pip (Python package manager)
   - virtualenv or venv

2. **SQLite Tools**
   - SQLite command-line tool
   - DB Browser for SQLite (recommended for visual inspection)

3. **Required Files**
   - Input CSV file with ad server data
   - Required CSV fields:
     - creative_id (required)
     - ad_tag (required)
     - ad_item_id (required)
     - campaign_id (required)
     - ad_type (required)
     - ad_item_keywords (optional)
     - ad_item_categories (optional)
     - creative_keywords (optional)
     - creative_categories (optional)

## Installation Steps

1. **Set Up Python Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   source venv/bin/activate  # On Unix/macOS
   # or
   .\venv\Scripts\activate  # On Windows
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the System**
   - All configuration is centralized in `click_ninja_army/config/config.py`
   - Review and update the following settings:
     ```python
     # API Configuration
     api.base_url = "https://dev.shyftcommerce.com/server"
     api.auth_token = "your-auth-token"
     api.publisher_id = "your-publisher-id"
     api.guest_id = "your-guest-id"
     
     # Worker Configuration
     worker_count = 5  # Adjust based on your needs
     request_timeout = 10
     
     # Rate Limiting
     rate_limit = 10.0  # requests per second
     burst_limit = 20   # maximum burst size
     ```

4. **Initialize Database**
   ```bash
   # The database will be automatically initialized on first run
   # or you can manually initialize it:
   python click_ninja_army/core/database_migration.py
   ```

## Running the System

1. **Process CSV Data**
   ```bash
   python click_ninja_army/core/data_transformer.py input.csv
   ```
   This will:
   - Validate the CSV data
   - Transform the data into campaign pool entries
   - Generate combinations for keywords and categories
   - Store entries in the database

2. **Generate Ad Requests (Scout Ninja)**
   ```bash
   python click_ninja_army/core/scout_ninja.py
   ```
   This will:
   - Process campaign pool entries
   - Generate ad requests with rate limiting
   - Store request IDs in the database
   - Track request generation metrics

3. **Process Impressions and Clicks (Strike Ninja)**
   ```bash
   python click_ninja_army/core/strike_ninja.py
   ```
   This will:
   - Process impressions and clicks in parallel
   - Use separate worker pools for each operation
   - Apply rate limiting per operation type
   - Track performance metrics

4. **Monitor Performance**
   ```bash
   python click_ninja_army/core/monitoring.py
   ```
   This will:
   - Display real-time performance metrics
   - Show worker pool statistics
   - Track success/failure rates
   - Monitor response times

## Database Management

1. **Using DB Browser for SQLite**
   - Download and install [DB Browser for SQLite](https://sqlitebrowser.org/)
   - Open `click_ninja.db` in DB Browser
   - Navigate through tables:
     - `campaign_pool`: Campaign and ad combinations
     - `request_pool`: Generated ad requests
     - `operation_log`: Impression and click operations
     - `performance_metrics`: System performance data

2. **Using SQLite Command Line**
   ```bash
   # Open database
   sqlite3 click_ninja.db
   
   # View tables
   .tables
   
   # View schema
   .schema
   
   # Query campaign pool
   SELECT * FROM campaign_pool WHERE status = 'pending';
   
   # Query operation log
   SELECT * FROM operation_log ORDER BY created_at DESC LIMIT 10;
   ```

## Monitoring and Debugging

1. **Check Request Status**
   ```sql
   SELECT status, COUNT(*) 
   FROM request_pool 
   GROUP BY status;
   ```

2. **View Recent Operations**
   ```sql
   SELECT 
       o.request_id,
       o.operation_type,
       o.status,
       o.error_message,
       o.created_at
   FROM operation_log o
   ORDER BY o.created_at DESC
   LIMIT 20;
   ```

3. **Check Performance Metrics**
   ```sql
   SELECT 
       category,
       metric_name,
       AVG(metric_value) as avg_value,
       MAX(metric_value) as max_value,
       MIN(metric_value) as min_value
   FROM performance_metrics
   GROUP BY category, metric_name;
   ```

## Worker Pool Configuration

The system uses separate worker pools for different operations:

1. **Scout Ninja Workers**
   - Handles ad request generation
   - Configurable worker count
   - Rate limiting per API endpoint
   - Automatic retry mechanism

2. **Strike Ninja Workers**
   - Separate pools for impressions and clicks
   - Configurable pool sizes
   - Independent rate limiting
   - Health monitoring and auto-scaling

## Troubleshooting

1. **Database Issues**
   - Verify database exists: `ls click_ninja.db`
   - Check permissions: `ls -l click_ninja.db`
   - Verify schema: `.schema` in SQLite command line

2. **API Issues**
   - Check API token in `config.py`
   - Verify API URL is accessible
   - Check rate limits in configuration
   - Review operation logs for errors

3. **Performance Issues**
   - Monitor worker pool utilization
   - Check rate limit settings
   - Review response times
   - Adjust worker pool sizes if needed

## Maintenance

1. **Backup Database**
   ```bash
   # Create backup
   cp click_ninja.db click_ninja.db.backup
   ```

2. **Clean Up Old Data**
   ```sql
   -- Remove completed requests older than 30 days
   DELETE FROM request_pool 
   WHERE status = 'completed' 
   AND created_at < datetime('now', '-30 days');
   ```

3. **Reset Database**
   ```bash
   # Remove existing database
   rm click_ninja.db
   
   # Reinitialize
   python click_ninja_army/core/database_migration.py
   ```

## Critical Notes

1. **API Configuration**
   - API tokens and endpoints are configured in `config.py`
   - Rate limits are enforced per operation type
   - Burst limits prevent API overload

2. **Data Processing**
   - CSV validation is strict
   - Keywords and categories are optional
   - Duplicate entries are automatically handled

3. **Performance**
   - Worker pools auto-scale based on load
   - Rate limiting prevents API throttling
   - Metrics are tracked per operation

4. **Security**
   - API tokens are stored in configuration
   - Input validation is thorough
   - Error handling is comprehensive