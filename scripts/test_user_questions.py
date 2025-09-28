#!/usr/bin/env python3
"""
測試用戶問題 - 專案、開源新手、Slack使用者頻率、活動問題
"""
import sys
import os
sys.path.append('/app')

import requests
import json
import time

def test_user_questions():
    """測試用戶問題"""
    print("🧪 測試用戶問題")
    print("=" * 60)
    
    # 測試問題列表
    test_questions = [
        {
            "category": "專案問題",
            "questions": [
                "介紹一下源來適你的專案",
                "Apache Kafka是什麼？",
                "Apache YuniKorn的程式語言是什麼？",
                "Apache Ambari的mentor是誰？",
                "KubeRay專案有什麼特色？"
            ]
        },
        {
            "category": "開源新手問題", 
            "questions": [
                "我是開源新手，應該從哪個專案開始？",
                "如何參與Apache專案？",
                "commitizen-tools適合新手嗎？",
                "新手如何貢獻開源專案？",
                "有哪些適合新手的good first issue？"
            ]
        },
        {
            "category": "Slack使用者頻率問題",
            "questions": [
                "誰是最活躍的用戶？",
                "第五活躍的使用者是誰？",
                "蔡嘉平發了多少條訊息？",
                "Jesse的活躍度如何？",
                "社群中最活躍的前10個用戶是誰？"
            ]
        },
        {
            "category": "活動問題",
            "questions": [
                "下週我們有什麼活動？",
                "這週有什麼meetup？",
                "科技開講是什麼時候？",
                "最近有什麼技術分享？",
                "下個月的活動安排？"
            ]
        }
    ]
    
    base_url = "http://localhost:8000"
    
    for category_info in test_questions:
        print(f"\n📂 {category_info['category']}:")
        print("-" * 40)
        
        for i, question in enumerate(category_info['questions'], 1):
            print(f"\n  {i}. 問題: {question}")
            
            try:
                # 發送問題到API
                response = requests.post(
                    f"{base_url}/ask_question",
                    json={"question": question},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('answer', '無回答')
                    
                    # 顯示回答（截取前200字符）
                    if len(answer) > 200:
                        answer = answer[:200] + "..."
                    
                    print(f"     回答: {answer}")
                    
                    # 檢查是否有用戶名稱顯示
                    if "user_" in answer:
                        print("     ⚠️  回答中包含匿名化ID")
                    elif any(name in answer for name in ["蔡嘉平", "Jesse", "劉哲佑", "Jason", "大神"]):
                        print("     ✅ 回答中顯示了真實用戶名稱")
                    else:
                        print("     ℹ️  回答中沒有用戶名稱相關內容")
                    
                    # 檢查來源數量
                    sources_used = result.get('sources_used', 0)
                    print(f"     來源數量: {sources_used}")
                    
                else:
                    print(f"     ❌ API錯誤: {response.status_code}")
                    print(f"     錯誤內容: {response.text}")
                    
            except requests.exceptions.Timeout:
                print("     ⏰ 請求超時")
            except requests.exceptions.ConnectionError:
                print("     🔌 連接錯誤")
            except Exception as e:
                print(f"     ❌ 其他錯誤: {e}")
            
            # 避免請求過於頻繁
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("🎉 用戶問題測試完成！")

if __name__ == "__main__":
    test_user_questions()
"""
測試用戶問題 - 專案、開源新手、Slack使用者頻率、活動問題
"""
import sys
import os
sys.path.append('/app')

import requests
import json
import time

def test_user_questions():
    """測試用戶問題"""
    print("🧪 測試用戶問題")
    print("=" * 60)
    
    # 測試問題列表
    test_questions = [
        {
            "category": "專案問題",
            "questions": [
                "介紹一下源來適你的專案",
                "Apache Kafka是什麼？",
                "Apache YuniKorn的程式語言是什麼？",
                "Apache Ambari的mentor是誰？",
                "KubeRay專案有什麼特色？"
            ]
        },
        {
            "category": "開源新手問題", 
            "questions": [
                "我是開源新手，應該從哪個專案開始？",
                "如何參與Apache專案？",
                "commitizen-tools適合新手嗎？",
                "新手如何貢獻開源專案？",
                "有哪些適合新手的good first issue？"
            ]
        },
        {
            "category": "Slack使用者頻率問題",
            "questions": [
                "誰是最活躍的用戶？",
                "第五活躍的使用者是誰？",
                "蔡嘉平發了多少條訊息？",
                "Jesse的活躍度如何？",
                "社群中最活躍的前10個用戶是誰？"
            ]
        },
        {
            "category": "活動問題",
            "questions": [
                "下週我們有什麼活動？",
                "這週有什麼meetup？",
                "科技開講是什麼時候？",
                "最近有什麼技術分享？",
                "下個月的活動安排？"
            ]
        }
    ]
    
    base_url = "http://localhost:8000"
    
    for category_info in test_questions:
        print(f"\n📂 {category_info['category']}:")
        print("-" * 40)
        
        for i, question in enumerate(category_info['questions'], 1):
            print(f"\n  {i}. 問題: {question}")
            
            try:
                # 發送問題到API
                response = requests.post(
                    f"{base_url}/ask_question",
                    json={"question": question},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result.get('answer', '無回答')
                    
                    # 顯示回答（截取前200字符）
                    if len(answer) > 200:
                        answer = answer[:200] + "..."
                    
                    print(f"     回答: {answer}")
                    
                    # 檢查是否有用戶名稱顯示
                    if "user_" in answer:
                        print("     ⚠️  回答中包含匿名化ID")
                    elif any(name in answer for name in ["蔡嘉平", "Jesse", "劉哲佑", "Jason", "大神"]):
                        print("     ✅ 回答中顯示了真實用戶名稱")
                    else:
                        print("     ℹ️  回答中沒有用戶名稱相關內容")
                    
                    # 檢查來源數量
                    sources_used = result.get('sources_used', 0)
                    print(f"     來源數量: {sources_used}")
                    
                else:
                    print(f"     ❌ API錯誤: {response.status_code}")
                    print(f"     錯誤內容: {response.text}")
                    
            except requests.exceptions.Timeout:
                print("     ⏰ 請求超時")
            except requests.exceptions.ConnectionError:
                print("     🔌 連接錯誤")
            except Exception as e:
                print(f"     ❌ 其他錯誤: {e}")
            
            # 避免請求過於頻繁
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("🎉 用戶問題測試完成！")

if __name__ == "__main__":
    test_user_questions()
