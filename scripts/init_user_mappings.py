#!/usr/bin/env python3
"""
初始化用戶映射腳本
添加示例用戶映射數據
"""
import os
import sys
import logging
from datetime import datetime

# 添加項目根目錄到Python路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.user_name_mapper import UserNameMapper

def init_sample_mappings():
    """初始化示例用戶映射"""
    mapper = UserNameMapper()
    
    # 示例用戶映射
    sample_mappings = [
        {
            'platform': 'slack',
            'original_user_id': 'U1234567890',
            'anonymized_id': 'user_12345678',
            'display_name': '蔡嘉平',
            'real_name': '蔡嘉平',
            'aliases': ['嘉平'],
            'group_terms': ['大神', '大佬', 'mentor', 'leader', '社群老大']
        },
        {
            'platform': 'slack',
            'original_user_id': 'U0987654321',
            'anonymized_id': 'user_87654321',
            'display_name': '莊偉赳',
            'real_name': '莊偉赳',
            'aliases': ['偉赳', 'Jesse'],
            'group_terms': ['大神', '大佬', '專家', '前輩']
        },
        {
            'platform': 'github',
            'original_user_id': 'jesse123',
            'anonymized_id': 'user_abcdef12',
            'display_name': 'Jesse',
            'real_name': 'Jesse',
            'aliases': ['偉赳', '莊偉赳'],
            'group_terms': ['大神', 'mentor']
        }
    ]
    
    print("開始初始化用戶映射...")
    
    for mapping in sample_mappings:
        try:
            success = mapper.add_user_mapping(
                platform=mapping['platform'],
                original_user_id=mapping['original_user_id'],
                anonymized_id=mapping['anonymized_id'],
                display_name=mapping['display_name'],
                real_name=mapping['real_name'],
                aliases=mapping['aliases'],
                group_terms=mapping['group_terms']
            )
            
            if success:
                print(f"✅ 成功添加用戶映射: {mapping['display_name']}")
            else:
                print(f"❌ 添加用戶映射失敗: {mapping['display_name']}")
                
        except Exception as e:
            print(f"❌ 添加用戶映射時發生錯誤 {mapping['display_name']}: {e}")
    
    print("\n用戶映射初始化完成！")
    
    # 顯示所有映射
    print("\n當前所有用戶映射:")
    all_mappings = mapper.get_all_mappings()
    for mapping in all_mappings:
        print(f"- {mapping.display_name} ({mapping.platform}): {mapping.aliases} | {mapping.group_terms}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_sample_mappings()

初始化用戶映射腳本
添加示例用戶映射數據
"""
import os
import sys
import logging
from datetime import datetime

# 添加項目根目錄到Python路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.user_name_mapper import UserNameMapper

def init_sample_mappings():
    """初始化示例用戶映射"""
    mapper = UserNameMapper()
    
    # 示例用戶映射
    sample_mappings = [
        {
            'platform': 'slack',
            'original_user_id': 'U1234567890',
            'anonymized_id': 'user_12345678',
            'display_name': '蔡嘉平',
            'real_name': '蔡嘉平',
            'aliases': ['嘉平'],
            'group_terms': ['大神', '大佬', 'mentor', 'leader', '社群老大']
        },
        {
            'platform': 'slack',
            'original_user_id': 'U0987654321',
            'anonymized_id': 'user_87654321',
            'display_name': '莊偉赳',
            'real_name': '莊偉赳',
            'aliases': ['偉赳', 'Jesse'],
            'group_terms': ['大神', '大佬', '專家', '前輩']
        },
        {
            'platform': 'github',
            'original_user_id': 'jesse123',
            'anonymized_id': 'user_abcdef12',
            'display_name': 'Jesse',
            'real_name': 'Jesse',
            'aliases': ['偉赳', '莊偉赳'],
            'group_terms': ['大神', 'mentor']
        }
    ]
    
    print("開始初始化用戶映射...")
    
    for mapping in sample_mappings:
        try:
            success = mapper.add_user_mapping(
                platform=mapping['platform'],
                original_user_id=mapping['original_user_id'],
                anonymized_id=mapping['anonymized_id'],
                display_name=mapping['display_name'],
                real_name=mapping['real_name'],
                aliases=mapping['aliases'],
                group_terms=mapping['group_terms']
            )
            
            if success:
                print(f"✅ 成功添加用戶映射: {mapping['display_name']}")
            else:
                print(f"❌ 添加用戶映射失敗: {mapping['display_name']}")
                
        except Exception as e:
            print(f"❌ 添加用戶映射時發生錯誤 {mapping['display_name']}: {e}")
    
    print("\n用戶映射初始化完成！")
    
    # 顯示所有映射
    print("\n當前所有用戶映射:")
    all_mappings = mapper.get_all_mappings()
    for mapping in all_mappings:
        print(f"- {mapping.display_name} ({mapping.platform}): {mapping.aliases} | {mapping.group_terms}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_sample_mappings()
