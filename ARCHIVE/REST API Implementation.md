# Implementation Plan: Move from GQL to REST

## Step 1: Analyze Current GQL Usage ✅
- GQL is **not directly used** in the codebase (no gql or graphql library imports or queries).
- The only reference to GQL is in the config: `ad_server_url` is set to `/server/graphql`.
- The ScoutNinja phase uses `requests.post` with the configured `api_url` and a custom payload.
- **Action:** To switch to REST, update the config to use the REST endpoint and refactor the payload logic as needed.

## Step 2: Map Data to REST Payloads (complete) ✅
- [x] Product ad type mapping implemented in ScoutNinja.
- [x] Display ad type mapping implemented in ScoutNinja.
- [x] Video ad type mapping implemented in ScoutNinja.
- [x] NativeFixed ad type mapping implemented in ScoutNinja.
- [x] NativeDynamic ad type mapping implemented in ScoutNinja.
- All major ad types are now supported for REST payloads in ScoutNinja.

## Step 3: Update Endpoint and Method ✅
- Change the endpoint from the GQL URL to the REST endpoint:
  - POST {ad-server-url}/rmn-requests
- Ensure the correct Content-Type: application/json header is set.

## Step 4: Refactor Request Generation Logic ✅
- [x] The GQL request logic has been fully replaced with REST logic in both Scout Ninja and Strike Ninja.
- [x] The system selects the correct REST payload template based on ad type, populates it with data, sends POST requests, and handles responses (including extracting adRequestId).

## Step 5: Update Error Handling and Logging ✅
- [x] Added a global failure counter and circuit breaker logic to both Scout Ninja and Strike Ninja.
- [x] If consecutive failures exceed a threshold, all workers are paused for a cooldown period, then resume.
- [x] Summary logging is added for circuit breaker events and when the system resumes.
- [x] The system now avoids endless worker spawning and API hammering during persistent backend errors.

## Step 6: Test Each Ad Type
- Use your runner script to test each ad type (Display, Product, Video, etc.) with the new REST logic.
- Compare the results with the expected output and ensure the system still populates the request pool correctly.

## Step 7: Clean Up and Document
- Remove any unused GQL code.
- Update documentation and config files to reflect the new REST API usage.