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
   - All configuration is now hardcoded in `click_ninja_army/config/config.py`.
   - Edit this file to set API URLs, tokens, database path, and other settings as needed.

4. **Initialize SQLite Database**
   ```bash
   # Create and initialize the database
   sqlite3 click_ninja.db < database.sql
   ```

## Running the System

1. **Process CSV Data**
   - Use your own script or interactive Python session to process CSVs using the DataTransformer and Database classes.

2. **Generate Requests**
   - Use your own script or interactive Python session to generate requests using the RequestGenerator and Database classes.

## Database Management

1. **Using DB Browser for SQLite**
   - Download and install [DB Browser for SQLite](https://sqlitebrowser.org/)
   - Open `click_ninja.db` in DB Browser
   - Navigate through tables:
     - `ad_requests`: View and manage requests
     - `operation_log`: Check operation history

2. **Using SQLite Command Line**
   ```bash
   # Open database
   sqlite3 click_ninja.db
   
   # View tables
   .tables
   
   # View schema
   .schema
   
   # Query requests
   SELECT * FROM ad_requests WHERE status = 'pending';
   
   # Query operation log
   SELECT * FROM operation_log ORDER BY started_at DESC LIMIT 10;
   
   # Exit
   .quit
   ```

## Monitoring and Debugging

1. **Check Request Status**
   ```sql
   -- In SQLite command line or DB Browser
   SELECT status, COUNT(*) 
   FROM ad_requests 
   GROUP BY status;
   ```

2. **View Recent Operations**
   ```sql
   SELECT 
       o.request_id,
       o.operation_type,
       o.success,
       o.error_message,
       o.started_at
   FROM operation_log o
   ORDER BY o.started_at DESC
   LIMIT 20;
   ```

3. **Check Failed Requests**
   ```sql
   SELECT 
       r.request_id,
       r.campaign_id,
       r.ad_type,
       o.error_message
   FROM ad_requests r
   JOIN operation_log o ON r.request_id = o.request_id
   WHERE r.status = 'failed'
   ORDER BY o.started_at DESC;
   ```

## Troubleshooting

1. **Database Issues**
   - Verify database exists: `ls click_ninja.db`
   - Check permissions: `ls -l click_ninja.db`
   - Verify schema: `.schema` in SQLite command line

2. **API Issues**
   - Check API token and URL in `config.py`
   - Verify API URL is accessible
   - Check rate limits

3. **Data Processing Issues**
   - Verify CSV format matches requirements
   - Check required fields are present
   - Review transformation logs

## Maintenance

1. **Backup Database**
   ```bash
   # Create backup
   cp click_ninja.db click_ninja.db.backup
   ```

2. **Clean Up Old Data**
   ```sql
   -- Remove completed requests older than 30 days
   DELETE FROM ad_requests 
   WHERE status = 'completed' 
   AND created_at < datetime('now', '-30 days');
   ```

3. **Reset Database**
   ```bash
   # Remove existing database
   rm click_ninja.db
   
   # Reinitialize
   sqlite3 click_ninja.db < database.sql
   ```