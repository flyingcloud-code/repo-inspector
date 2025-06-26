#!/usr/bin/env python3
from neo4j import GraphDatabase
import sys

def test_connection():
    try:
        # 创建驱动连接
        driver = GraphDatabase.driver(
            "bolt://localhost:7687", 
            auth=("neo4j", "neo4j")  # 尝试使用默认密码
        )
        
        # 验证连接
        driver.verify_connectivity()
        print("✅ 成功连接到Neo4j数据库")
        
        # 测试简单查询
        with driver.session() as session:
            result = session.run("RETURN 1 AS num")
            record = result.single()
            if record and record["num"] == 1:
                print("✅ 查询测试成功")
            else:
                print("❌ 查询测试失败")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j连接错误: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1) 