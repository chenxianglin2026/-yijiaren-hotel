"""
伊家人酒店系统 - pytest 配置 & 测试数据初始化
每次运行测试前自动重置种子数据，解决"测试数据耗尽"问题
"""
import pytest
import sys
import os

# 确保 backend 目录在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session", autouse=True)
def reset_test_data():
    """
    测试会话级 fixture：在运行任何测试前，强制重置数据库到初始种子状态。
    这样每次 pytest 运行都从一个干净的状态开始。
    """
    print("\n🔄 [conftest] 重置测试数据...")
    try:
        from seed_mock import reset_db, seed
        reset_db()
        seed(force=True)
        print("✅ [conftest] 测试数据已重置")
    except Exception as e:
        print(f"⚠️  [conftest] 重置测试数据失败: {e}")
        # 不阻断测试，让测试自己报告数据问题
