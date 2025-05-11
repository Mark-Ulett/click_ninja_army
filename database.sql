-- Simplified SQLite schema for Click Ninja Army

-- Main requests table
CREATE TABLE IF NOT EXISTS ad_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT UNIQUE NOT NULL,
    campaign_id TEXT NOT NULL,
    ad_item_id TEXT NOT NULL,
    ad_tag TEXT NOT NULL,
    ad_type TEXT NOT NULL,
    page_category_ids TEXT,  -- Stored as comma-separated values
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('pending', 'in_progress', 'completed', 'failed'))
);

-- Operation logging table
CREATE TABLE IF NOT EXISTS operation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success INTEGER DEFAULT 0,  -- SQLite uses INTEGER for boolean
    error_message TEXT,
    FOREIGN KEY(request_id) REFERENCES ad_requests(request_id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ad_requests_status ON ad_requests(status);
CREATE INDEX IF NOT EXISTS idx_ad_requests_campaign ON ad_requests(campaign_id);
CREATE INDEX IF NOT EXISTS idx_operation_log_request_id ON operation_log(request_id);

-- Create trigger for updated_at
CREATE TRIGGER update_ad_requests_timestamp 
AFTER UPDATE ON ad_requests
BEGIN
    UPDATE ad_requests SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END; 