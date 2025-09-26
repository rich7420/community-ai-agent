#!/usr/bin/env python3
"""
Docker設置測試腳本
測試Docker Compose配置和服務
"""
import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def test_docker_available():
    """測試Docker是否可用"""
    print("🐳 測試Docker可用性...")
    
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker可用: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Docker不可用: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Docker未安裝")
        return False
    except Exception as e:
        print(f"❌ Docker測試失敗: {e}")
        return False

def test_docker_compose_available():
    """測試Docker Compose是否可用"""
    print("\n🐙 測試Docker Compose可用性...")
    
    try:
        result = subprocess.run(['docker-compose', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Docker Compose可用: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Docker Compose不可用: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Docker Compose未安裝")
        return False
    except Exception as e:
        print(f"❌ Docker Compose測試失敗: {e}")
        return False

def test_docker_compose_config():
    """測試Docker Compose配置文件"""
    print("\n📋 測試Docker Compose配置...")
    
    compose_file = "docker-compose.yml"
    if not os.path.exists(compose_file):
        print(f"❌ 找不到 {compose_file}")
        return False
    
    try:
        result = subprocess.run(['docker-compose', 'config'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker Compose配置文件語法正確")
            return True
        else:
            print(f"❌ Docker Compose配置錯誤: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Docker Compose配置測試失敗: {e}")
        return False

def test_docker_images():
    """測試Docker鏡像構建"""
    print("\n🏗️  測試Docker鏡像構建...")
    
    try:
        # 測試PostgreSQL Dockerfile
        postgres_dockerfile = "docker/postgres/Dockerfile"
        if os.path.exists(postgres_dockerfile):
            print(f"✅ PostgreSQL Dockerfile存在: {postgres_dockerfile}")
        else:
            print(f"❌ PostgreSQL Dockerfile不存在: {postgres_dockerfile}")
            return False
        
        # 測試主應用Dockerfile
        main_dockerfile = "Dockerfile"
        if os.path.exists(main_dockerfile):
            print(f"✅ 主應用Dockerfile存在: {main_dockerfile}")
        else:
            print(f"❌ 主應用Dockerfile不存在: {main_dockerfile}")
            return False
        
        # 測試前端Dockerfile
        frontend_dockerfile = "docker/frontend/Dockerfile"
        if os.path.exists(frontend_dockerfile):
            print(f"✅ 前端Dockerfile存在: {frontend_dockerfile}")
        else:
            print(f"❌ 前端Dockerfile不存在: {frontend_dockerfile}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Docker鏡像測試失敗: {e}")
        return False

def test_environment_files():
    """測試環境配置文件"""
    print("\n🔧 測試環境配置文件...")
    
    files_to_check = [
        "env.example",
        ".env",
        "config/settings.py",
        "config/data_sources.yaml",
        "requirements.txt"
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path} 存在")
        else:
            print(f"❌ {file_path} 不存在")
            all_exist = False
    
    return all_exist

def test_database_init_script():
    """測試資料庫初始化腳本"""
    print("\n🗄️  測試資料庫初始化腳本...")
    
    init_script = "scripts/init_db.py"
    if not os.path.exists(init_script):
        print(f"❌ 資料庫初始化腳本不存在: {init_script}")
        return False
    
    # 檢查腳本是否可執行
    if os.access(init_script, os.R_OK):
        print(f"✅ 資料庫初始化腳本可讀: {init_script}")
    else:
        print(f"❌ 資料庫初始化腳本不可讀: {init_script}")
        return False
    
    return True

def main():
    """主測試函數"""
    print("🚀 開始Docker設置測試...\n")
    
    tests = [
        test_docker_available,
        test_docker_compose_available,
        test_docker_compose_config,
        test_docker_images,
        test_environment_files,
        test_database_init_script
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 測試 {test_func.__name__} 失敗: {e}")
            results.append(False)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n📊 測試結果總結:")
    print(f"   成功: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("🎉 Docker設置測試完成！")
        print("✅ 所有組件已準備就緒，可以進行Docker Compose部署")
        return True
    else:
        print("⚠️  部分Docker設置測試失敗")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
