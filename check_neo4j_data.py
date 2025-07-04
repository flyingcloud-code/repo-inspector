#!/usr/bin/env python3
"""
检查Neo4j数据库中的数据
"""

import logging
import random
import sys
from pathlib import Path

# 将项目根目录添加到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.llm.service_factory import ServiceFactory
from src.code_learner.core.data_models import Function

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Neo4jChecker:
    """
    一个用于检查Neo4j数据库中代码图谱完整性的工具。
    """
    def __init__(self, graph_store: Neo4jGraphStore):
        self.graph_store = graph_store
        self.project_id = graph_store.project_id
        if not self.project_id:
            raise ValueError("Checker must be initialized with a store that has a project_id.")

    def run_all_checks(self):
        """运行所有检查并打印报告。"""
        logger.info(f"🚀 开始对项目 '{self.project_id}' 进行数据库完整性检查...")
        
        results = {
            "节点检查": self.check_node_counts(),
            "关系检查": self.check_relationship_counts(),
            "函数属性抽查": self.check_random_function_properties(),
        }

        self.print_report(results)

    def check_node_counts(self) -> dict:
        """检查核心节点类型的数量。"""
        logger.info("  - 正在检查节点数量...")
        node_counts = {}
        for label in ["File", "Function", "Module"]:
            query = f"MATCH (n:{label} {{project_id: $project_id}}) RETURN count(n) AS count"
            result = self.graph_store.query(query, {'project_id': self.project_id})
            record = result[0] if result else None
            count = record["count"] if record else 0
            node_counts[label] = count
            logger.info(f"    - 发现 {count} 个 {label} 节点")
        return node_counts

    def check_relationship_counts(self) -> dict:
        """检查核心关系类型的数量。"""
        logger.info("  - 正在检查关系数量...")
        rel_counts = {}
        for rel_type in ["CONTAINS", "BELONGS_TO", "CALLS", "DEPENDS_ON"]:
            query = f"MATCH ()-[r:{rel_type}]->() WHERE (startNode(r).project_id = $project_id OR endNode(r).project_id = $project_id) RETURN count(r) AS count"
            result = self.graph_store.query(query, {'project_id': self.project_id})
            record = result[0] if result else None
            count = record["count"] if record else 0
            rel_counts[rel_type] = count
            logger.info(f"    - 发现 {count} 个 :{rel_type} 关系")
        return rel_counts

    def check_random_function_properties(self, sample_size: int = 3) -> dict:
        """随机抽查一些函数节点的属性是否完整。"""
        logger.info(f"  - 正在随机抽查 {sample_size} 个函数的属性...")
            query = """
        MATCH (f:Function {project_id: $project_id})
        WHERE f.docstring IS NOT NULL AND f.docstring <> ''
        RETURN f
        ORDER BY rand()
        LIMIT $limit
            """
        results = self.graph_store.query(query, {'project_id': self.project_id, 'limit': sample_size})
        
        records = results
        checked_functions = {}
        if not records:
            logger.warning("    - 未找到任何带有注释的函数进行抽查。")
            return {"抽查结果": "未找到样本"}

        for record in records:
            node = record["f"]
            func_name = node.get("name")
            properties_status = {
                "docstring_ok": bool(node.get("docstring", "").strip()),
                "return_type_ok": node.get("return_type") is not None,
                "parameters_ok": node.get("parameters") is not None,
            }
            checked_functions[func_name] = properties_status
            logger.info(f"    - 抽查函数 '{func_name}': {properties_status}")
            
        return checked_functions

    def print_report(self, results: dict):
        """打印最终的检查报告。"""
        print("\n" + "="*50)
        print(f"🔬 Neo4j 数据库质检报告 (项目ID: {self.project_id})")
        print("="*50)

        # 节点报告
        print("\n--- 节点统计 ---")
        node_counts = results.get("节点检查", {})
        for label, count in node_counts.items():
            status = "✅" if count > 0 else "❌"
            print(f"  {status} {label} 节点: {count}")
        
        # 关系报告
        print("\n--- 关系统计 ---")
        rel_counts = results.get("关系检查", {})
        for rel_type, count in rel_counts.items():
            # CALLS 关系是我们的重点关注对象
            is_critical_and_missing = rel_type == "CALLS" and count == 0
            status = "❌" if is_critical_and_missing else "✅"
            if count == 0 and rel_type != "CALLS":
                status = "⚠️" # 其他关系缺失是警告
            
            print(f"  {status} :{rel_type} 关系: {count}")
        
        if rel_counts.get("CALLS", 0) == 0:
            print("\n  [!!] 严重问题: 未发现任何 :CALLS 调用关系！")

        # 属性抽查报告
        print("\n--- 函数属性抽查 ---")
        prop_checks = results.get("函数属性抽查", {})
        if not prop_checks or "抽查结果" in prop_checks:
            print("  ⚠️ 未能执行有效的属性抽查。")
            else:
            for func_name, statuses in prop_checks.items():
                all_ok = all(statuses.values())
                status = "✅" if all_ok else "❌"
                print(f"  {status} 函数 '{func_name}':")
                for prop, ok in statuses.items():
                    prop_status = "✅" if ok else "❌"
                    print(f"    - {prop_status} {prop}")
        
        print("\n" + "="*50)
        print("报告结束")
        print("="*50 + "\n")


def main():
    """主函数，运行检查器。"""
    # 请在这里设置你要检查的项目ID
    project_id_to_check = "auto_086e94dd"

    logger.info(f"准备检查项目: {project_id_to_check}")
    
    try:
        # 使用服务工厂来获取已配置的图存储实例
        service_factory = ServiceFactory()
        graph_store = service_factory.get_graph_store(project_id=project_id_to_check)

        if not graph_store or not graph_store.connected:
            logger.error("无法连接到 Neo4j 数据库，请检查配置和数据库状态。")
            return

        checker = Neo4jChecker(graph_store)
        checker.run_all_checks()

    except Exception as e:
        logger.error(f"执行检查时发生意外错误: {e}", exc_info=True)

if __name__ == "__main__":
    main() 