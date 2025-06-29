#!/usr/bin/env python3
"""
检查Neo4j数据库中的数据
"""

import sys
import logging
from src.code_learner.storage.neo4j_store import Neo4jGraphStore

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    # 获取项目ID，如果提供的话
    project_id = sys.argv[1] if len(sys.argv) > 1 else "auto_086e94dd"
    
    print(f"检查Neo4j数据库中的数据 (项目ID: {project_id})")
    
    # 创建Neo4j连接
    graph_store = Neo4jGraphStore(project_id=project_id)
    graph_store.connect()
    
    try:
        # 1. 检查节点数量
        node_count = graph_store.count_nodes()
        rel_count = graph_store.count_relationships()
        print(f"节点数量: {node_count}")
        print(f"关系数量: {rel_count}")
        
        # 2. 检查节点类型
        node_types = graph_store.get_node_types()
        print(f"节点类型: {node_types}")
        
        # 3. 检查关系类型
        rel_types = graph_store.get_relationship_types()
        print(f"关系类型: {rel_types}")
        
        # 4. 检查函数节点数量
        function_count = graph_store.count_nodes_by_label("Function")
        print(f"函数节点数量: {function_count}")
        
        # 5. 检查文件节点数量
        file_count = graph_store.count_nodes_by_label("File")
        print(f"文件节点数量: {file_count}")
        
        # 6. 查询部分函数节点
        print("\n查询部分函数节点:")
        with graph_store.driver.session() as session:
            query = """
            MATCH (f:Function)
            WHERE f.project_id = $project_id
            RETURN f.name as name, f.file_path as file_path
            LIMIT 10
            """
            result = session.run(query, project_id=project_id)
            
            for record in result:
                print(f"函数: {record['name']}, 文件: {record['file_path']}")
        
        # 7. 查询是否存在特定函数
        print("\n查询特定函数:")
        function_names = ["sbi_cppc_writable", "sbi_hart_pmp_configure", "sbi_system_suspend_set_device"]
        for function_name in function_names:
            function_node = graph_store.get_function_by_name(function_name)
            if function_node:
                print(f"找到函数: {function_name}, 文件: {function_node.get('file_path', 'unknown')}")
            else:
                print(f"未找到函数: {function_name}")
        
        # 8. 查询调用关系
        print("\n查询调用关系:")
        with graph_store.driver.session() as session:
            query = """
            MATCH (caller:Function)-[r:CALLS]->(callee:Function)
            WHERE caller.project_id = $project_id
            RETURN caller.name as caller, callee.name as callee
            LIMIT 10
            """
            result = session.run(query, project_id=project_id)
            
            count = 0
            for record in result:
                print(f"调用关系: {record['caller']} -> {record['callee']}")
                count += 1
            
            if count == 0:
                print("未找到任何调用关系")
    
    finally:
        # 关闭连接
        graph_store.close()

if __name__ == "__main__":
    main() 