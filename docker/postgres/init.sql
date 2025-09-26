-- Enable pgvector extension (temporarily disabled for ARM64 compatibility)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- Create community_data table
CREATE TABLE IF NOT EXISTS community_data (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,  -- 'slack', 'github', 'facebook'
    content TEXT NOT NULL,
    author_anon TEXT,  -- Anonymized author identifier
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_url TEXT,
    metadata JSONB,  -- Additional metadata
    embedding TEXT,  -- Vector embedding for similarity search (temporarily as TEXT for ARM64 compatibility)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_community_data_platform ON community_data(platform);
CREATE INDEX IF NOT EXISTS idx_community_data_timestamp ON community_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_community_data_author ON community_data(author_anon);
-- CREATE INDEX IF NOT EXISTS idx_community_data_embedding ON community_data USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create opt-out table for users who want to exclude their data
CREATE TABLE IF NOT EXISTS opt_out_users (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,
    user_identifier TEXT NOT NULL,  -- Original user identifier
    anon_identifier TEXT NOT NULL,  -- Anonymized identifier
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform, user_identifier)
);

-- Create weekly reports table
CREATE TABLE IF NOT EXISTS weekly_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE NOT NULL,
    report_content TEXT NOT NULL,
    report_type TEXT DEFAULT 'weekly',  -- 'weekly', 'monthly', etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(report_date, report_type)
);

-- Create data collection logs table
CREATE TABLE IF NOT EXISTS collection_logs (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,
    collection_type TEXT NOT NULL,  -- 'slack', 'github', 'facebook'
    status TEXT NOT NULL,  -- 'success', 'failed', 'partial'
    records_collected INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
CREATE TRIGGER update_community_data_updated_at 
    BEFORE UPDATE ON community_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create partitioned table for better performance
CREATE TABLE IF NOT EXISTS community_data_partitioned (
    LIKE community_data INCLUDING ALL
) PARTITION BY RANGE (timestamp);

-- Create monthly partitions for the current year and next year
DO $$
DECLARE
    start_date DATE;
    end_date DATE;
    partition_name TEXT;
BEGIN
    -- Create partitions for current year
    FOR i IN 0..11 LOOP
        start_date := DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' * i;
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'community_data_' || TO_CHAR(start_date, 'YYYY_MM');
        
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF community_data_partitioned 
                       FOR VALUES FROM (%L) TO (%L)', 
                       partition_name, start_date, end_date);
    END LOOP;
    
    -- Create partitions for next year
    FOR i IN 0..11 LOOP
        start_date := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 year') + INTERVAL '1 month' * i;
        end_date := start_date + INTERVAL '1 month';
        partition_name := 'community_data_' || TO_CHAR(start_date, 'YYYY_MM');
        
        EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF community_data_partitioned 
                       FOR VALUES FROM (%L) TO (%L)', 
                       partition_name, start_date, end_date);
    END LOOP;
END $$;

-- Create function to automatically create new partitions
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    partition_name := table_name || '_' || TO_CHAR(start_date, 'YYYY_MM');
    end_date := start_date + INTERVAL '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I 
                   FOR VALUES FROM (%L) TO (%L)', 
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;

-- Create function to clean up old partitions
CREATE OR REPLACE FUNCTION cleanup_old_partitions(table_name TEXT, months_to_keep INTEGER DEFAULT 12)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    cutoff_date DATE;
BEGIN
    cutoff_date := CURRENT_DATE - INTERVAL '1 month' * months_to_keep;
    
    FOR partition_name IN 
        SELECT schemaname||'.'||tablename 
        FROM pg_tables 
        WHERE tablename LIKE table_name || '_%' 
        AND tablename ~ '^\d{4}_\d{2}$'
        AND TO_DATE(SUBSTRING(tablename FROM '(\d{4}_\d{2})$'), 'YYYY_MM') < cutoff_date
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || partition_name;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
