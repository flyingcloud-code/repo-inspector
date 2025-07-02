#!/usr/bin/env python3
"""
更新函数代码工具

从源文件中读取函数代码并更新到Neo4j数据库中。
"""

import logging
import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from code_learner.storage.neo4j_store import Neo4jGraphStore
from neo4j import Result

# 配置日志
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_function_code(function_name: str, project_id=None):
    """更新函数代码
    
    Args:
        function_name: 函数名
        project_id: 项目ID
    """
    store = Neo4jGraphStore(project_id=project_id)
    
    try:
        # 连接到Neo4j数据库
        store.connect()
        
        # 查询函数节点
        query = """
        MATCH (file:File)-[:CONTAINS]->(f:Function {name: $name})
        RETURN f.name as name, file.path as file_path, f.code as code,
               f.start_line as start_line, f.end_line as end_line, id(f) as id
        """
        
        with store.driver.session() as session:
            result = session.run(query, {"name": function_name})
            records = list(result)
            
            if not records:
                logger.warning(f"未找到函数 {function_name}")
                return
            
            logger.info(f"找到 {len(records)} 个函数节点")
            
            # 处理每个函数节点
            for i, record in enumerate(records):
                node_id = record["id"]
                file_path = record["file_path"]
                start_line = record["start_line"]
                end_line = record["end_line"]
                
                logger.info(f"处理节点 {i+1}:")
                logger.info(f"  文件路径: {file_path}")
                logger.info(f"  行范围: {start_line}-{end_line}")
                
                # 尝试读取代码
                code = None
                
                # 首先尝试绝对路径
                if os.path.isabs(file_path) and os.path.exists(file_path):
                    try:
                        code = read_function_from_file(file_path, start_line, end_line)
                        logger.info("  从绝对路径读取代码成功")
                    except Exception as e:
                        logger.error(f"  从绝对路径读取代码失败: {e}")
                
                # 如果绝对路径失败，尝试相对于项目根目录的路径
                if not code:
                    project_root = Path(__file__).parent.parent.parent.parent
                    rel_path = os.path.join(project_root, file_path)
                    if os.path.exists(rel_path):
                        try:
                            code = read_function_from_file(rel_path, start_line, end_line)
                            logger.info("  从相对路径读取代码成功")
                        except Exception as e:
                            logger.error(f"  从相对路径读取代码失败: {e}")
                
                # 如果成功读取到代码，更新数据库
                if code:
                    logger.info(f"  代码长度: {len(code)} 字符")
                    
                    # 更新函数节点的代码
                    update_query = """
                    MATCH (f:Function)
                    WHERE id(f) = $node_id
                    SET f.code = $code
                    """
                    
                    try:
                        session.run(update_query, {"node_id": node_id, "code": code})
                        logger.info("  更新代码成功")
                    except Exception as e:
                        logger.error(f"  更新代码失败: {e}")
                else:
                    logger.warning("  未能读取到代码")
    
    except Exception as e:
        logger.error(f"更新函数代码失败: {e}")
    finally:
        # 关闭连接
        store.close()

def read_function_from_file(file_path, start_line, end_line):
    """从文件中读取函数代码
    
    Args:
        file_path: 文件路径
        start_line: 起始行
        end_line: 结束行
        
    Returns:
        str: 函数代码
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            # 行号从1开始，但列表索引从0开始
            start_idx = start_line - 1
            end_idx = end_line
            
            if start_idx < 0:
                start_idx = 0
            if end_idx > len(lines):
                end_idx = len(lines)
            
            code_lines = lines[start_idx:end_idx]
            return ''.join(code_lines)
    except Exception as e:
        logger.error(f"读取文件失败: {e}")
        return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="更新函数代码")
    parser.add_argument("function_name", help="函数名")
    parser.add_argument("--project-id", help="项目ID")
    
    args = parser.parse_args()
    update_function_code(args.function_name, args.project_id)

if __name__ == "__main__":
    main() 