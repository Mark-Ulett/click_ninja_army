# Full Test Sequence for Click Ninja Army (Log-Based Validation)

## 1. Activate the Virtual Environment

```bash
# On Unix/macOS
source venv/bin/activate

# On Windows
.\venv\Scripts\activate
```

## 2. Prepare a Test CSV

* Ensure your input.csv contains at least one entry for each ad type you want to test (Product, Display, Video, NativeFixed, NativeDynamic)
* Each row should have the required fields: creative_id, ad_tag, ad_item_id, campaign_id, ad_type, etc.

**note:** Use the file Campaign_11369.csv for testing

## 3. Process the CSV (Campaign Pool Generation)

```bash
python click_ninja_army/core/data_transformer.py input.csv
```

**Check logs:**
* Look for messages about rows processed, entries generated, and any validation errors

🗂️ What to check in the database:
- The request_pool (or equivalent) table should now contain 169 new entries, each corresponding to a unique combination of ad type, creative, keyword, and/or category from the CSV.
- Each entry should have the correct campaign_id, ad_type, creative_id, and other relevant fields as per the CSV.
📜 What to check in the logs:
- Messages about each row being processed and validated.
- Confirmation of each entry being inserted (with unique IDs).
- A summary stating the number of rows processed and entries generated.
- No errors or validation failures.

## 4. Generate Ad Requests (Scout Ninja)

```bash
python click_ninja_army/core/scout_ninja.py
```

**Check logs:**
* Look for:
  * "Started X worker threads"
  * "Queued N entries for request generation"
  * "Request generation failed…" (for errors)
  * "Circuit breaker tripped…" (if persistent failures)
  * "Requests generated: N" (for success)

**Expected:**
* For valid API/config, you should see successful ad request generation for each ad type
* If you intentionally misconfigure the endpoint, you should see the circuit breaker activate after repeated failures

## 5. Process Impressions and Clicks (Strike Ninja)

```bash
python click_ninja_army/core/strike_ninja.py
```

**Check logs:**
* Look for:
  * "Started X impression workers and Y click workers"
  * "Queued impression for requestId: …"
  * "Queued click for adRequestId: …"
  * "Impression/click failed…" (for errors)
  * "StrikeNinja Circuit breaker tripped…" (if persistent failures)
  * "Impression/click sent" (for success)

**Expected:**
* Impressions and clicks should be processed for all ad types with valid adRequestIds
* Circuit breaker should activate if there are repeated failures

## 6. Monitor Performance (Optional)

```bash
python click_ninja_army/core/monitoring.py
```

**Check logs/console:**
* Real-time stats on worker pools, queue sizes, error rates, and performance metrics

## 7. Inspect the Database (Optional)

* Use DB Browser for SQLite or the CLI to check:
  * request_pool for generated requests and their statuses
  * operation_log for impression/click outcomes
  * performance_metrics for success/failure rates