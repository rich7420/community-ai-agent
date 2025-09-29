-- Using TEXT for embedding storage instead of pgvector for better compatibility

-- Create community_data table
CREATE TABLE IF NOT EXISTS community_data (
    id TEXT PRIMARY KEY,  -- Changed from SERIAL to TEXT to support string IDs
    platform TEXT NOT NULL,  -- 'slack', 'github', 'facebook'
    content TEXT NOT NULL,
    author_anon TEXT,  -- Anonymized author identifier
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_url TEXT,
    metadata JSONB,  -- Additional metadata
    embedding TEXT,  -- Vector embedding stored as JSON text for compatibility
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_community_data_platform ON community_data(platform);
CREATE INDEX IF NOT EXISTS idx_community_data_timestamp ON community_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_community_data_author ON community_data(author_anon);
-- Embedding index removed as we use FAISS for vector similarity search

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

-- Create user name mapping table for displaying real names instead of anonymized IDs
CREATE TABLE IF NOT EXISTS user_name_mappings (
    id SERIAL PRIMARY KEY,
    platform TEXT NOT NULL,  -- 'slack', 'github', 'facebook'
    original_user_id TEXT NOT NULL,  -- Original user identifier from platform
    anonymized_id TEXT NOT NULL,  -- Anonymized identifier used in data
    display_name TEXT NOT NULL,  -- Preferred display name (e.g., "蔡嘉平", "Jesse")
    real_name TEXT,  -- Real name if available
    aliases TEXT[],  -- Array of aliases (e.g., ["偉赳", "jonas"])
    group_terms TEXT[],  -- Group terms this user might be referred to (e.g., ["大神", "大佬"])
    is_active BOOLEAN DEFAULT TRUE,  -- Whether this mapping is active
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(platform, original_user_id)
);

-- Create indexes for user name mappings
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_anon_id ON user_name_mappings(anonymized_id);
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_display_name ON user_name_mappings(display_name);
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_aliases ON user_name_mappings USING GIN(aliases);
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_group_terms ON user_name_mappings USING GIN(group_terms);

-- Create project descriptions table for accurate project information
CREATE TABLE IF NOT EXISTS project_descriptions (
    id TEXT PRIMARY KEY,
    repository TEXT NOT NULL UNIQUE,  -- Format: owner/repo
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    readme_content TEXT,  -- Full README content
    source TEXT NOT NULL,  -- 'github_readme', 'ai_generated', 'manual'
    confidence_score FLOAT DEFAULT 0.0,  -- 0-1 confidence score
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_verified BOOLEAN DEFAULT FALSE,
    metadata JSONB,  -- Additional metadata like stars, forks, topics
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for project descriptions
CREATE INDEX IF NOT EXISTS idx_project_descriptions_repository ON project_descriptions(repository);
CREATE INDEX IF NOT EXISTS idx_project_descriptions_source ON project_descriptions(source);
CREATE INDEX IF NOT EXISTS idx_project_descriptions_confidence ON project_descriptions(confidence_score);
CREATE INDEX IF NOT EXISTS idx_project_descriptions_verified ON project_descriptions(is_verified);

-- Create Google Calendar events table
CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,  -- Google Calendar event ID
    calendar_id TEXT NOT NULL,  -- Google Calendar ID
    title TEXT NOT NULL,
    description TEXT,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    location TEXT,
    attendees JSONB,  -- Array of attendee information
    creator_email TEXT,
    organizer_email TEXT,
    status TEXT,  -- 'confirmed', 'tentative', 'cancelled'
    visibility TEXT,  -- 'default', 'public', 'private'
    recurrence TEXT,  -- Recurrence rule if applicable
    source_url TEXT,  -- Link to the event in Google Calendar
    metadata JSONB,  -- Additional metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for calendar events
CREATE INDEX IF NOT EXISTS idx_calendar_events_calendar_id ON calendar_events(calendar_id);
CREATE INDEX IF NOT EXISTS idx_calendar_events_start_time ON calendar_events(start_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_end_time ON calendar_events(end_time);
CREATE INDEX IF NOT EXISTS idx_calendar_events_status ON calendar_events(status);
CREATE INDEX IF NOT EXISTS idx_calendar_events_title ON calendar_events USING GIN(to_tsvector('english', title));

-- Create Google Calendar calendars table
CREATE TABLE IF NOT EXISTS google_calendars (
    id TEXT PRIMARY KEY,  -- Google Calendar ID
    name TEXT NOT NULL,
    description TEXT,
    timezone TEXT,
    access_role TEXT,  -- 'owner', 'reader', 'writer', 'freeBusyReader'
    is_primary BOOLEAN DEFAULT FALSE,
    is_selected BOOLEAN DEFAULT TRUE,
    color_id TEXT,
    background_color TEXT,
    foreground_color TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for google calendars
CREATE INDEX IF NOT EXISTS idx_google_calendars_name ON google_calendars(name);
CREATE INDEX IF NOT EXISTS idx_google_calendars_is_primary ON google_calendars(is_primary);
CREATE INDEX IF NOT EXISTS idx_google_calendars_is_selected ON google_calendars(is_selected);

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

-- Create triggers for calendar tables
CREATE TRIGGER update_calendar_events_updated_at
    BEFORE UPDATE ON calendar_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_google_calendars_updated_at
    BEFORE UPDATE ON google_calendars 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create partitioned table for better performance
CREATE TABLE IF NOT EXISTS community_data_partitioned (
    id TEXT NOT NULL,
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    author_anon TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_url TEXT,
    metadata JSONB,
    embedding TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create indexes for the partitioned table
CREATE INDEX IF NOT EXISTS idx_community_data_partitioned_platform ON community_data_partitioned(platform);
CREATE INDEX IF NOT EXISTS idx_community_data_partitioned_timestamp ON community_data_partitioned(timestamp);
CREATE INDEX IF NOT EXISTS idx_community_data_partitioned_author ON community_data_partitioned(author_anon);

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
