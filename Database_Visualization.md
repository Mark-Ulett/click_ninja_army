# Click Ninja Army Database Visualization Guide

## Database Overview

The Click Ninja Army uses SQLite as its database system, with two main tables:

1. `request_pool` - Stores ad request information
2. `operation_log` - Tracks operation execution history

## Database Location

The database file is located at: `click_ninja.db` in your project root directory.

## Visualization Options

### 1. Using SQLite Browser (Recommended)

1. Install DB Browser for SQLite:
   - macOS: `brew install --cask db-browser-for-sqlite`
   - Windows: Download from [sqlitebrowser.org](https://sqlitebrowser.org/)
   - Linux: `sudo apt-get install sqlitebrowser`

2. Open the database:
   - Launch DB Browser for SQLite
   - Click "Open Database"
   - Navigate to your project directory
   - Select `click_ninja.db`

3. Explore the database:
   - Browse Data: View and edit table contents
   - Execute SQL: Run custom queries
   - Database Structure: View table schemas and relationships

### 2. Using Command Line

1. Open SQLite CLI:
```bash
sqlite3 click_ninja.db
```

2. Useful commands:
```sql
-- View all tables
.tables

-- View table schema
.schema request_pool
.schema operation_log

-- View recent requests
SELECT * FROM request_pool ORDER BY created_at DESC LIMIT 10;

-- View recent operations
SELECT * FROM operation_log ORDER BY created_at DESC LIMIT 10;

-- View success rate
SELECT 
    operation_type,
    COUNT(*) as total_operations,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_operations,
    ROUND(AVG(response_time), 2) as avg_response_time
FROM operation_log
GROUP BY operation_type;

-- Exit SQLite CLI
.quit
```

### 3. Using Python Script

Create a file named `db_visualizer.py`:

```python
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def visualize_database():
    # Connect to database
    conn = sqlite3.connect('click_ninja.db')
    
    # Load data into pandas DataFrames
    requests_df = pd.read_sql_query("SELECT * FROM request_pool", conn)
    operations_df = pd.read_sql_query("SELECT * FROM operation_log", conn)
    
    # Create visualizations
    plt.figure(figsize=(12, 6))
    
    # Request status distribution
    plt.subplot(1, 2, 1)
    requests_df['status'].value_counts().plot(kind='pie', autopct='%1.1f%%')
    plt.title('Request Status Distribution')
    
    # Operation success rate
    plt.subplot(1, 2, 2)
    operations_df['status'].value_counts().plot(kind='bar')
    plt.title('Operation Status Distribution')
    
    plt.tight_layout()
    plt.savefig('database_visualization.png')
    plt.close()
    
    # Print summary statistics
    print("\nRequest Pool Summary:")
    print(requests_df.describe())
    print("\nOperation Log Summary:")
    print(operations_df.describe())
    
    conn.close()

if __name__ == "__main__":
    visualize_database()
```

Run the script:
```bash
python db_visualizer.py
```

## Database Schema

### request_pool Table
```sql
CREATE TABLE request_pool (
    id INTEGER PRIMARY KEY,
    request_id TEXT UNIQUE NOT NULL,
    campaign_id TEXT NOT NULL,
    ad_item_id TEXT,
    ad_tag TEXT NOT NULL,
    ad_type TEXT NOT NULL,
    page_category_ids TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    retries INTEGER DEFAULT 0,
    last_attempt TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### operation_log Table
```sql
CREATE TABLE operation_log (
    id INTEGER PRIMARY KEY,
    request_id TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    response_time FLOAT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Common Queries

### Request Analysis
```sql
-- Get pending requests
SELECT * FROM request_pool WHERE status = 'pending';

-- Get failed requests
SELECT * FROM request_pool WHERE status = 'failed';

-- Get request success rate by campaign
SELECT 
    campaign_id,
    COUNT(*) as total_requests,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_requests
FROM request_pool
GROUP BY campaign_id;
```

### Operation Analysis
```sql
-- Get operation success rate
SELECT 
    operation_type,
    COUNT(*) as total_operations,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_operations
FROM operation_log
GROUP BY operation_type;

-- Get average response time by operation type
SELECT 
    operation_type,
    ROUND(AVG(response_time), 2) as avg_response_time
FROM operation_log
GROUP BY operation_type;
```

## Tips for Database Management

1. **Regular Backups**
   - Create regular backups of your database file
   - Use the `.backup` command in SQLite CLI

2. **Performance Optimization**
   - Use indexes for frequently queried columns
   - Regularly vacuum the database to reclaim space
   - Monitor database size and growth

3. **Data Cleanup**
   - Archive old data periodically
   - Remove failed requests after analysis
   - Clean up operation logs older than a certain date

## Need Help?

If you encounter any issues or need assistance:
1. Check the logs in your project directory
2. Review the database schema documentation
3. Contact the development team for support

Remember: Always make a backup before making significant changes to the database! 