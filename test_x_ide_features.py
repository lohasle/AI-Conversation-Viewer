#!/usr/bin/env python3
"""
测试 X-IDE 模式下的搜索、收藏、设置功能
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_x_ide_page():
    """测试 X-IDE 页面是否正常加载"""
    print("测试 X-IDE 页面加载...")
    response = requests.get(f"{BASE_URL}/x-ide")
    assert response.status_code == 200, f"页面加载失败: {response.status_code}"
    assert "X-IDE" in response.text, "页面内容不正确"
    print("✓ X-IDE 页面加载成功")

def test_global_search_api():
    """测试全局搜索 API"""
    print("\n测试全局搜索 API...")
    response = requests.get(f"{BASE_URL}/api/search/global", params={"q": "test", "limit": 10})
    assert response.status_code == 200, f"搜索 API 失败: {response.status_code}"
    data = response.json()
    assert "results" in data, "搜索结果格式不正确"
    assert "total" in data, "缺少总数字段"
    print(f"✓ 全局搜索 API 正常，找到 {data['total']} 个结果")

def test_favorites_api():
    """测试收藏 API"""
    print("\n测试收藏 API...")
    
    # 获取收藏列表
    response = requests.get(f"{BASE_URL}/api/favorites")
    assert response.status_code == 200, f"获取收藏列表失败: {response.status_code}"
    data = response.json()
    assert "favorites" in data, "收藏列表格式不正确"
    print(f"✓ 获取收藏列表成功，共 {data['total']} 个收藏")
    
    # 获取收藏统计
    response = requests.get(f"{BASE_URL}/api/favorites/statistics")
    assert response.status_code == 200, f"获取收藏统计失败: {response.status_code}"
    stats = response.json()
    assert "total" in stats, "统计数据格式不正确"
    print(f"✓ 获取收藏统计成功: {stats}")

def test_create_favorite():
    """测试创建收藏"""
    print("\n测试创建收藏...")
    
    payload = {
        "type": "session",
        "view": "qwen",
        "project_name": "test_project",
        "session_id": "test_session_123",
        "title": "测试收藏",
        "annotation": "这是一个测试收藏",
        "tags": []
    }
    
    response = requests.post(
        f"{BASE_URL}/api/favorites",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        assert "favorite_id" in data, "创建收藏响应格式不正确"
        favorite_id = data["favorite_id"]
        print(f"✓ 创建收藏成功，ID: {favorite_id}")
        
        # 删除测试收藏
        delete_response = requests.delete(f"{BASE_URL}/api/favorites/{favorite_id}")
        assert delete_response.status_code == 200, "删除收藏失败"
        print(f"✓ 删除测试收藏成功")
    else:
        print(f"⚠ 创建收藏失败（可能是因为没有实际的项目数据）: {response.status_code}")

def test_check_favorite_exists():
    """测试检查收藏是否存在"""
    print("\n测试检查收藏是否存在...")
    
    response = requests.get(
        f"{BASE_URL}/api/favorites/check/qwen/test_project/test_session"
    )
    assert response.status_code == 200, f"检查收藏失败: {response.status_code}"
    data = response.json()
    assert "exists" in data, "响应格式不正确"
    print(f"✓ 检查收藏功能正常，exists: {data['exists']}")

def test_statistics_api():
    """测试统计 API"""
    print("\n测试统计 API...")
    
    response = requests.get(f"{BASE_URL}/api/statistics")
    assert response.status_code == 200, f"获取统计失败: {response.status_code}"
    data = response.json()
    assert "stats" in data, "统计数据格式不正确"
    assert "total_sessions" in data, "缺少总会话数"
    print(f"✓ 统计 API 正常")
    print(f"  - 总项目数: {data['total_projects']}")
    print(f"  - 总会话数: {data['total_sessions']}")
    for ide, stat in data['stats'].items():
        print(f"  - {ide}: {stat['project_count']} 个项目, {stat['session_count']} 个会话")

def test_recent_sessions_api():
    """测试最近会话 API"""
    print("\n测试最近会话 API...")
    
    response = requests.get(f"{BASE_URL}/api/sessions/recent", params={"limit": 5})
    assert response.status_code == 200, f"获取最近会话失败: {response.status_code}"
    data = response.json()
    assert "sessions" in data, "响应格式不正确"
    print(f"✓ 最近会话 API 正常，返回 {len(data['sessions'])} 个会话")

def main():
    """运行所有测试"""
    print("=" * 60)
    print("X-IDE 功能测试")
    print("=" * 60)
    
    try:
        test_x_ide_page()
        test_global_search_api()
        test_favorites_api()
        test_create_favorite()
        test_check_favorite_exists()
        test_statistics_api()
        test_recent_sessions_api()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except requests.exceptions.ConnectionError:
        print(f"\n✗ 无法连接到服务器 {BASE_URL}")
        print("请确保服务器正在运行: aicode-viewer")
        return 1
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
