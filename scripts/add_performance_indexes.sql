-- 性能優化索引
-- 為用戶活躍度查詢添加索引

-- 1. 為 user_name_mappings 表添加索引
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_display_name ON user_name_mappings USING gin(to_tsvector('simple', display_name));
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_real_name ON user_name_mappings USING gin(to_tsvector('simple', real_name));
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_aliases ON user_name_mappings USING gin(aliases);
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_group_terms ON user_name_mappings USING gin(group_terms);

-- 2. 為 community_data 表添加複合索引
CREATE INDEX IF NOT EXISTS idx_community_data_author_anon ON community_data (author_anon);
CREATE INDEX IF NOT EXISTS idx_community_data_platform_author ON community_data (platform, author_anon);
CREATE INDEX IF NOT EXISTS idx_community_data_timestamp ON community_data (timestamp DESC);

-- 3. 為 JSON 字段添加索引
CREATE INDEX IF NOT EXISTS idx_community_data_channel ON community_data USING gin((metadata->>'channel'));
CREATE INDEX IF NOT EXISTS idx_community_data_channel_name ON community_data USING gin((metadata->>'channel_name'));
CREATE INDEX IF NOT EXISTS idx_community_data_is_thread_reply ON community_data ((metadata->>'is_thread_reply'));

-- 4. 為用戶活躍度查詢優化的複合索引
CREATE INDEX IF NOT EXISTS idx_community_data_user_activity ON community_data (author_anon, platform, timestamp DESC) 
WHERE platform = 'slack';

-- 5. 為統計查詢優化的索引
CREATE INDEX IF NOT EXISTS idx_community_data_stats ON community_data (author_anon, metadata->>'is_thread_reply', timestamp);
-- 為用戶活躍度查詢添加索引

-- 1. 為 user_name_mappings 表添加索引
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_display_name ON user_name_mappings USING gin(to_tsvector('simple', display_name));
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_real_name ON user_name_mappings USING gin(to_tsvector('simple', real_name));
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_aliases ON user_name_mappings USING gin(aliases);
CREATE INDEX IF NOT EXISTS idx_user_name_mappings_group_terms ON user_name_mappings USING gin(group_terms);

-- 2. 為 community_data 表添加複合索引
CREATE INDEX IF NOT EXISTS idx_community_data_author_anon ON community_data (author_anon);
CREATE INDEX IF NOT EXISTS idx_community_data_platform_author ON community_data (platform, author_anon);
CREATE INDEX IF NOT EXISTS idx_community_data_timestamp ON community_data (timestamp DESC);

-- 3. 為 JSON 字段添加索引
CREATE INDEX IF NOT EXISTS idx_community_data_channel ON community_data USING gin((metadata->>'channel'));
CREATE INDEX IF NOT EXISTS idx_community_data_channel_name ON community_data USING gin((metadata->>'channel_name'));
CREATE INDEX IF NOT EXISTS idx_community_data_is_thread_reply ON community_data ((metadata->>'is_thread_reply'));

-- 4. 為用戶活躍度查詢優化的複合索引
CREATE INDEX IF NOT EXISTS idx_community_data_user_activity ON community_data (author_anon, platform, timestamp DESC) 
WHERE platform = 'slack';

-- 5. 為統計查詢優化的索引
CREATE INDEX IF NOT EXISTS idx_community_data_stats ON community_data (author_anon, metadata->>'is_thread_reply', timestamp);
