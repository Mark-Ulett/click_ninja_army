# Click Ninja Army Use Cases

This document provides practical examples and use cases for the Click Ninja Army system.

## Example 1: Basic Campaign Processing

### Scenario
You have a CSV file containing ad campaign data for a new product launch. The campaign includes multiple ad items with different keywords and categories.

### Input CSV Format
```csv
creative_id,ad_tag,ad_item_id,campaign_id,ad_type,ad_item_keywords,ad_item_categories,creative_keywords,creative_categories
CR123,AT456,AI789,CAMP001,banner,summer sale,clothing,summer deals,apparel
CR124,AT457,AI790,CAMP001,banner,clearance,shoes,shoe sale,footwear
CR125,AT458,AI791,CAMP001,video,new arrival,accessories,new items,accessories
```

### Step-by-Step Process

1. **Prepare the Environment**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure the System**
   ```python
   # In click_ninja_army/config/config.py
   api.base_url = "https://dev.shyftcommerce.com/server"
   api.auth_token = "your-auth-token"
   api.publisher_id = "PET67"
   api.guest_id = "G-PET34567"
   
   # Adjust worker settings for your needs
   worker_count = 5
   rate_limit = 10.0
   burst_limit = 20
   ```

3. **Process the Campaign**
   ```bash
   # Transform and validate the CSV data
   python click_ninja_army/core/data_transformer.py campaign_data.csv
   
   # Generate ad requests
   python click_ninja_army/core/scout_ninja.py
   
   # Process impressions and clicks
   python click_ninja_army/core/strike_ninja.py
   ```

4. **Monitor Progress**
   ```bash
   # Check real-time metrics
   python click_ninja_army/core/monitoring.py
   ```

5. **Verify Results**
   ```sql
   -- Check campaign pool entries
   SELECT COUNT(*) as total_entries,
          COUNT(CASE WHEN keyword IS NOT NULL THEN 1 END) as with_keywords,
          COUNT(CASE WHEN category IS NOT NULL THEN 1 END) as with_categories
   FROM campaign_pool
   WHERE campaign_id = 'CAMP001';
   
   -- Check request generation status
   SELECT status, COUNT(*) as count
   FROM request_pool
   GROUP BY status;
   
   -- Check operation success rates
   SELECT operation_type,
          COUNT(*) as total_ops,
          SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successes
   FROM operation_log
   GROUP BY operation_type;
   ```

## Example 2: High-Volume Campaign with Rate Limiting

### Scenario
You need to process a large campaign with 10,000 ad items, each with multiple keywords and categories. The API has strict rate limits.

### Configuration Adjustments
```python
# In click_ninja_army/config/config.py
# Adjust for high volume
worker_count = 10
rate_limit = 5.0  # More conservative rate limit
burst_limit = 10  # Smaller burst size

# Configure worker pools
impression_workers = WorkerPoolConfig(
    min_workers=5,
    max_workers=20,
    queue_size=2000,
    idle_timeout=120.0
)

click_workers = WorkerPoolConfig(
    min_workers=3,
    max_workers=10,
    queue_size=1000,
    idle_timeout=120.0
)
```

### Processing Strategy
1. **Batch Processing**
   ```bash
   # Process in batches of 1000
   for i in {1..10}; do
     python click_ninja_army/core/data_transformer.py campaign_data_${i}.csv
     sleep 60  # Wait between batches
   done
   ```

2. **Monitor Worker Health**
   ```sql
   -- Check worker utilization
   SELECT pool_name,
          active_workers,
          total_tasks,
          avg_task_time,
          utilization
   FROM worker_metrics
   ORDER BY timestamp DESC
   LIMIT 10;
   ```

3. **Track Performance**
   ```sql
   -- Monitor response times
   SELECT operation_type,
          AVG(response_time) as avg_response,
          MAX(response_time) as max_response,
          COUNT(*) as total_ops
   FROM operation_log
   WHERE created_at > datetime('now', '-1 hour')
   GROUP BY operation_type;
   ```

## Example 3: Error Recovery and Retry

### Scenario
During processing, some requests fail due to temporary API issues. You need to retry failed operations.

### Recovery Process
1. **Identify Failed Requests**
   ```sql
   -- Find failed requests
   SELECT r.request_id,
          r.campaign_id,
          o.operation_type,
          o.error_message,
          o.created_at
   FROM request_pool r
   JOIN operation_log o ON r.request_id = o.request_id
   WHERE o.status = 'failed'
   AND o.created_at > datetime('now', '-1 hour');
   ```

2. **Retry Failed Operations**
   ```python
   # In click_ninja_army/core/strike_ninja.py
   # The system automatically retries failed operations
   # with exponential backoff
   max_retries = 3
   retry_delay = 1.0  # Base delay in seconds
   ```

3. **Monitor Retry Success**
   ```sql
   -- Check retry success rates
   SELECT operation_type,
          COUNT(*) as total_retries,
          SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_retries
   FROM operation_log
   WHERE retry_count > 0
   GROUP BY operation_type;
   ```

## Example 4: Performance Optimization

### Scenario
You need to optimize the system for maximum throughput while maintaining API rate limits.

### Optimization Steps
1. **Adjust Worker Pools**
   ```python
   # In click_ninja_army/config/config.py
   # Optimize for your specific workload
   impression_workers = WorkerPoolConfig(
       min_workers=10,
       max_workers=30,
       queue_size=5000,
       idle_timeout=60.0,
       max_tasks_per_worker=2000
   )
   
   click_workers = WorkerPoolConfig(
       min_workers=5,
       max_workers=15,
       queue_size=2500,
       idle_timeout=60.0,
       max_tasks_per_worker=2000
   )
   ```

2. **Monitor Performance Metrics**
   ```sql
   -- Track system performance
   SELECT category,
          metric_name,
          AVG(metric_value) as avg_value,
          MAX(metric_value) as max_value,
          MIN(metric_value) as min_value
   FROM performance_metrics
   WHERE timestamp > datetime('now', '-1 hour')
   GROUP BY category, metric_name;
   ```

3. **Optimize Database**
   ```sql
   -- Create additional indexes if needed
   CREATE INDEX IF NOT EXISTS idx_operation_log_timestamp 
   ON operation_log(created_at);
   
   CREATE INDEX IF NOT EXISTS idx_request_pool_status 
   ON request_pool(status);
   ```

## Best Practices

1. **Data Preparation**
   - Validate CSV data before processing
   - Use consistent formatting for keywords and categories
   - Include all required fields

2. **Configuration**
   - Start with conservative rate limits
   - Monitor and adjust worker pools based on performance
   - Keep API tokens secure

3. **Monitoring**
   - Regularly check performance metrics
   - Monitor worker pool health
   - Track error rates and response times

4. **Error Handling**
   - Review error logs regularly
   - Implement appropriate retry strategies
   - Maintain backup of important data

5. **Performance**
   - Optimize worker pool sizes for your workload
   - Monitor and adjust rate limits
   - Keep database indexes up to date 