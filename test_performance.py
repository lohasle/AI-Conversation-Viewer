#!/usr/bin/env python3
"""
性能测试脚本
测试缓存优化前后的性能差异
"""

import time
import requests
import statistics
from typing import List, Callable
from tabulate import tabulate


BASE_URL = "http://localhost:8000"


def measure_time(func: Callable, iterations: int = 5) -> tuple:
    """
    测量函数执行时间
    
    Returns:
        (平均时间, 最小时间, 最大时间, 标准差)
    """
    times = []
    for _ in range(iterations):
        start = time.time()
        func()
        elapsed = time.time() - start
        times.append(elapsed)
    
    return (
        statistics.mean(times),
        min(times),
        max(times),
        statistics.stdev(times) if len(times) > 1 else 0
    )


def test_projects_api():
    """测试项目列表 API"""
    response = requests.get(f"{BASE_URL}/api/projects?view=qwen")
    assert response.status_code == 200
    return response.json()


def test_sessions_api():
    """测试会话列表 API"""
    # 先获取项目列表
    projects = test_projects_api()
    if not projects:
        return []
    
    project_name = projects[0]['name']
    response = requests.get(f"{BASE_URL}/api/sessions/{project_name}?view=qwen")
    assert response.status_code == 200
    return response.json()


def test_conversation_api():
    """测试会话内容 API"""
    sessions = test_sessions_api()
    if not sessions:
        return {}
    
    projects = test_projects_api()
    project_name = projects[0]['name']
    session_id = sessions[0]['id']
    
    response = requests.get(
        f"{BASE_URL}/api/conversation/{project_name}/{session_id}?view=qwen"
    )
    assert response.status_code == 200
    return response.json()


def test_search_api():
    """测试搜索 API"""
    response = requests.get(f"{BASE_URL}/api/search/global?q=test&limit=10")
    assert response.status_code == 200
    return response.json()


def test_favorites_api():
    """测试收藏 API"""
    response = requests.get(f"{BASE_URL}/api/favorites?limit=50")
    assert response.status_code == 200
    return response.json()


def test_statistics_api():
    """测试统计 API"""
    response = requests.get(f"{BASE_URL}/api/statistics")
    assert response.status_code == 200
    return response.json()


def clear_cache():
    """清除所有缓存"""
    response = requests.post(f"{BASE_URL}/api/cache/clear?cache_type=all")
    assert response.status_code == 200


def get_cache_stats():
    """获取缓存统计"""
    response = requests.get(f"{BASE_URL}/api/cache/stats")
    assert response.status_code == 200
    return response.json()


def run_performance_tests():
    """运行性能测试"""
    print("=" * 80)
    print("性能测试 - AI Conversation Viewer")
    print("=" * 80)
    print()
    
    tests = [
        ("项目列表 API", test_projects_api),
        ("会话列表 API", test_sessions_api),
        ("会话内容 API", test_conversation_api),
        ("全局搜索 API", test_search_api),
        ("收藏列表 API", test_favorites_api),
        ("统计数据 API", test_statistics_api),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"测试: {test_name}")
        
        # 清除缓存，测试冷启动性能
        print("  - 清除缓存...")
        clear_cache()
        time.sleep(0.5)
        
        print("  - 测试冷启动性能（无缓存）...")
        try:
            cold_avg, cold_min, cold_max, cold_std = measure_time(test_func, iterations=3)
        except Exception as e:
            print(f"    ⚠ 测试失败: {e}")
            continue
        
        # 测试热启动性能（有缓存）
        print("  - 测试热启动性能（有缓存）...")
        hot_avg, hot_min, hot_max, hot_std = measure_time(test_func, iterations=5)
        
        # 计算性能提升
        improvement = (cold_avg / hot_avg) if hot_avg > 0 else 0
        
        results.append([
            test_name,
            f"{cold_avg*1000:.1f}ms",
            f"{hot_avg*1000:.1f}ms",
            f"{improvement:.1f}x",
            f"{cold_std*1000:.1f}ms",
            f"{hot_std*1000:.1f}ms"
        ])
        
        print(f"    ✓ 冷启动: {cold_avg*1000:.1f}ms (±{cold_std*1000:.1f}ms)")
        print(f"    ✓ 热启动: {hot_avg*1000:.1f}ms (±{hot_std*1000:.1f}ms)")
        print(f"    ✓ 性能提升: {improvement:.1f}x")
        print()
    
    # 显示结果表格
    print("=" * 80)
    print("性能测试结果汇总")
    print("=" * 80)
    print()
    
    headers = ["测试项", "冷启动", "热启动", "提升", "冷启动标准差", "热启动标准差"]
    print(tabulate(results, headers=headers, tablefmt="grid"))
    print()
    
    # 显示缓存统计
    print("=" * 80)
    print("缓存统计")
    print("=" * 80)
    print()
    
    cache_stats = get_cache_stats()
    cache_table = [[k, v] for k, v in cache_stats.items()]
    print(tabulate(cache_table, headers=["缓存类型", "条目数"], tablefmt="grid"))
    print()
    
    # 计算平均性能提升
    improvements = [float(row[3].replace('x', '')) for row in results]
    avg_improvement = statistics.mean(improvements)
    
    print("=" * 80)
    print(f"平均性能提升: {avg_improvement:.1f}x")
    print("=" * 80)


def run_stress_test():
    """运行压力测试"""
    print("\n" + "=" * 80)
    print("压力测试 - 并发请求")
    print("=" * 80)
    print()
    
    import concurrent.futures
    
    def make_request():
        try:
            response = requests.get(f"{BASE_URL}/api/projects?view=qwen", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    # 测试不同并发级别
    concurrency_levels = [1, 5, 10, 20]
    results = []
    
    for concurrency in concurrency_levels:
        print(f"测试并发级别: {concurrency}")
        
        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(make_request) for _ in range(concurrency * 10)]
            success_count = sum(1 for f in concurrent.futures.as_completed(futures) if f.result())
        
        elapsed = time.time() - start
        rps = (concurrency * 10) / elapsed
        
        results.append([
            concurrency,
            concurrency * 10,
            success_count,
            f"{elapsed:.2f}s",
            f"{rps:.1f}"
        ])
        
        print(f"  ✓ 总请求: {concurrency * 10}")
        print(f"  ✓ 成功: {success_count}")
        print(f"  ✓ 耗时: {elapsed:.2f}s")
        print(f"  ✓ RPS: {rps:.1f}")
        print()
    
    headers = ["并发数", "总请求", "成功数", "耗时", "RPS"]
    print(tabulate(results, headers=headers, tablefmt="grid"))


def main():
    """主函数"""
    try:
        # 检查服务器是否运行
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print(f"✗ 服务器未正常运行: {BASE_URL}")
            return 1
    except requests.exceptions.ConnectionError:
        print(f"✗ 无法连接到服务器: {BASE_URL}")
        print("请确保服务器正在运行: aicode-viewer")
        return 1
    
    print(f"✓ 服务器运行正常: {BASE_URL}\n")
    
    # 运行性能测试
    run_performance_tests()
    
    # 运行压力测试
    try:
        run_stress_test()
    except ImportError:
        print("\n⚠ 跳过压力测试（需要安装 concurrent.futures）")
    
    print("\n" + "=" * 80)
    print("✓ 所有测试完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        print("\n\n✗ 测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
