# Click Ninja Army: Configuration Summary

This document provides a complete summary of all configuration options available in `click_ninja_army/config/config.py`.
All configuration is hardcoded in this file and can be edited directly to suit your environment and requirements.

---

## Configuration Fields

| Field            | Type    | Default Value                              | Description                                      |
|------------------|---------|--------------------------------------------|--------------------------------------------------|
| api_url          | str     | "https://dev.shyftcommerce.com/server"     | The base URL for the ad request API.             |
| api_token        | str     | "your_token_here"                          | The API authentication token.                    |
| publisher_id     | str     | "PET67"                                    | The publisher ID for API requests.               |
| guest_id         | str     | "G-PET34567"                               | The guest ID for API requests.                   |
| db_path          | str     | "click_ninja.db"                           | Path to the SQLite database file.                |
| worker_count     | int     | 5                                          | Number of worker threads for processing.         |
| request_timeout  | int     | 10                                         | Timeout (in seconds) for API requests.           |
| rate_limit       | float   | 10.0                                       | Max requests per second (rate limiting).         |
| burst_limit      | int     | 20                                         | Max burst size for rate limiting.                |
| debug_mode       | bool    | True                                       | Enable debug mode (for development).             |
| test_mode        | bool    | False                                      | Enable test mode (for development/testing).      |

---

## Database Configuration

The system uses SQLite with the following tables:

1. **request_pool**
   - Stores ad requests and their status
   - Tracks request lifecycle
   - Manages request priorities
   - Records retry attempts

2. **operation_log**
   - Logs all operations
   - Tracks success/failure
   - Records response times
   - Stores error messages

---

## Worker Pool Configuration

The worker pool is configured with:

1. **Thread Management**
   - Maximum worker threads
   - Task queue size
   - Thread timeout settings

2. **Task Processing**
   - Task timeout
   - Error handling
   - Resource limits

---

## API Configuration

The API integration is configured with:

1. **Authentication**
   - API token
   - Publisher ID
   - Guest ID

2. **Request Settings**
   - Base URL
   - Timeout
   - Rate limits
   - Burst limits

---

## How to Edit Configuration

1. Open `click_ninja_army/config/config.py` in your editor.
2. Change the values of any fields as needed for your environment.
3. Save the file. No restart or reload is needed unless your application is running.

---

## Example

```python
from click_ninja_army.config.config import config

print(config.api_url)        # Prints the API base URL
print(config.db_path)        # Prints the SQLite database path
print(config.worker_count)   # Prints the number of worker threads
```

---

## Notes
- No environment variables or .env files are used.
- All configuration is visible and auditable in a single file.
- For security, do not commit sensitive tokens to public repositories.

---

For any changes to configuration, always update `config.py` and review this summary for clarity. 