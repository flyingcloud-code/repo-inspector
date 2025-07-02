#!/usr/bin/env python3
"""
检查Neo4j数据库中的函数

用于检查Neo4j数据库中是否存在特定函数，以及其关联的文件和代码。
"""

import logging
import sys
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from code_learner.storage.neo4j_store import Neo4jGraphStore
from neo4j import Result

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_function(function_name: str, project_id: Optional[str] = None):
    """检查函数是否存在
    
    Args:
        function_name: 函数名
        project_id: 项目ID
    """
    store = Neo4jGraphStore(project_id=project_id)
    
    try:
        # 连接到Neo4j数据库
        store.connect()
        
        # 查询函数节点
        query1 = """
        MATCH (f:Function)
        WHERE f.name = $name
        RETURN f.name as name, f.file_path as file_path, f.code as code,
               f.start_line as start_line, f.end_line as end_line
        """
        
        with store.driver.session() as session:
            result1: Result = session.run(query1, {"name": function_name})
            records1 = list(result1)
            
            print(f"查询1: 找到 {len(records1)} 个函数节点")
            for i, record in enumerate(records1):
                print(f"  节点 {i+1}:")
                print(f"    名称: {record['name']}")
                print(f"    文件路径: {record['file_path']}")
                print(f"    起始行: {record['start_line']}")
                print(f"    结束行: {record['end_line']}")
                print(f"    代码: {'有' if record['code'] else '无'}")
        
        # 查询函数与文件的关系
        query2 = """
        MATCH (file:File)-[:CONTAINS]->(f:Function)
        WHERE f.name = $name
        RETURN f.name as name, file.path as file_path, f.code as code,
               f.start_line as start_line, f.end_line as end_line
        """
        
        with store.driver.session() as session:
            result2: Result = session.run(query2, {"name": function_name})
            records2 = list(result2)
            
            print(f"\n查询2: 找到 {len(records2)} 个函数-文件关系")
            for i, record in enumerate(records2):
                print(f"  关系 {i+1}:")
                print(f"    函数名称: {record['name']}")
                print(f"    文件路径: {record['file_path']}")
                print(f"    起始行: {record['start_line']}")
                print(f"    结束行: {record['end_line']}")
                print(f"    代码: {'有' if record['code'] else '无'}")
        
        # 查询调用关系
        query3 = """
        MATCH (caller:Function)-[:CALLS]->(callee:Function)
        WHERE callee.name = $name
        RETURN caller.name as caller_name
        """
        
        with store.driver.session() as session:
            result3: Result = session.run(query3, {"name": function_name})
            records3 = list(result3)
            
            print(f"\n查询3: 找到 {len(records3)} 个调用者")
            for i, record in enumerate(records3):
                print(f"  调用者 {i+1}: {record['caller_name']}")
        
        # 查询被调用关系
        query4 = """
        MATCH (caller:Function)-[:CALLS]->(callee:Function)
        WHERE caller.name = $name
        RETURN callee.name as callee_name
        """
        
        with store.driver.session() as session:
            result4: Result = session.run(query4, {"name": function_name})
            records4 = list(result4)
            
            print(f"\n查询4: 找到 {len(records4)} 个被调用者")
            for i, record in enumerate(records4):
                print(f"  被调用者 {i+1}: {record['callee_name']}")
    
    except Exception as e:
        logger.error(f"检查函数失败: {e}")
    finally:
        # 关闭连接
        store.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="检查Neo4j数据库中的函数")
    parser.add_argument("function_name", help="要检查的函数名")
    parser.add_argument("--project-id", help="项目ID")
    
    args = parser.parse_args()
    check_function(args.function_name, args.project_id)

if __name__ == "__main__":
    main() 