# Click Ninja Army Test Procedures

## Pre-Test Checklist

- [ ] Verify API token is valid (set in `config.py`)
- [ ] Ensure database directory is writable (default: `click_ninja.db` in project root)
- [ ] Prepare test CSV files (e.g., `campaign_12476_DEV.csv`)
- [ ] Set up log directory (should be created automatically by the system)
- [ ] Verify rate limits with server team (configured in `config.py`)
- [ ] Document test scenarios (see below)
- [ ] Set up monitoring for test runs (log files, error alerts)

---

## Test Scenarios

### 1. Basic End-to-End Flow
- **Goal:** Validate that the system can process a CSV, transform data, generate requests, and execute operations.
- **Steps:**
  1. Place a sample CSV (e.g., `campaign_12476_DEV.csv`) in the project directory.
  2. Run the main workflow (via coordinator or script).
  3. Monitor logs for successful data transformation, request generation, and operation execution.
  4. Check the database for new request entries and operation logs.

### 2. Data Validation and Transformation
- **Goal:** Ensure invalid or malformed rows are skipped and logged.
- **Steps:**
  1. Add rows with missing required fields or malformed category IDs to the CSV.
  2. Run the workflow.
  3. Confirm that invalid rows are logged as warnings/errors and not processed further.

### 3. API Communication
- **Goal:** Confirm that requests are sent to the API and responses are handled.
- **Steps:**
  1. Use a valid API token and endpoint.
  2. Run the workflow and monitor logs for API request/response details.
  3. Simulate API failures (e.g., by using an invalid token) and confirm error logging.

### 4. Database Operations
- **Goal:** Validate that requests and operations are correctly logged in the database.
- **Steps:**
  1. After running the workflow, inspect the `click_ninja.db` database.
  2. Check the `request_pool` and `operation_log` tables for expected entries.

### 5. Rate Limiting
- **Goal:** Ensure the system respects configured rate limits.
- **Steps:**
  1. Set a low rate limit in `config.py`.
  2. Run the workflow and monitor logs for rate limit messages.

### 6. Error Handling
- **Goal:** Confirm that errors are logged and do not crash the system.
- **Steps:**
  1. Introduce errors (e.g., invalid CSV, API failures, DB write errors).
  2. Monitor logs for error messages and graceful handling.

---

## Expected Data Formats

### CSV Input
- **Required Columns:**
  - `campaign_id`, `ad_item_id`, `ad_tag`, `ad_type`, `ad_item_categories`
- **Optional Columns:**
  - `creative_id`, `creative_name`, `ad_size`, `page_type`, etc.
- **Category IDs:**
  - Format: `{1019,1007,1006}` (as a string)

### Transformed Data (Dictionary)
```
{
  'campaign_id': '12476',
  'ad_item_id': '24130',
  'ad_tag': 'petco/ad_tag',
  'ad_type': 'PRODUCT',
  'page_category_ids': [1019, 1007, 1006]
}
```

---

## Error Handling Procedures

- **Invalid Data:**
  - Rows failing validation are logged as warnings/errors and skipped.
- **API Failures:**
  - Errors are logged; requests are retried or marked as failed.
- **Database Errors:**
  - Errors are logged; system attempts to continue processing other requests.
- **Rate Limit Exceeded:**
  - System waits and retries as per configuration; logs rate limit events.
- **Unexpected Exceptions:**
  - All exceptions are logged with stack traces for debugging.

---

## Monitoring and Logs
- All logs are written to the `logs/` directory and to the console.
- Monitor logs for INFO, WARNING, and ERROR messages.
- Review log files after each test run for issues and performance metrics.

---

## Notes
- All configuration is hardcoded in `config.py` (no environment files).
- Test data should be realistic and cover edge cases.
- Comment out or reduce logging after initial testing to improve performance. 