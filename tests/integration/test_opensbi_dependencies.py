import unittest
import os
from pathlib import Path

from code_learner.llm.dependency_service import DependencyService
from code_learner.parser.c_parser import CParser
from code_learner.storage.neo4j_store import Neo4jGraphStore


class TestOpenSBIDependencies(unittest.TestCase):
    """OpenSBI项目依赖关系分析集成测试"""
    
    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        # 使用真实的OpenSBI代码路径
        cls.opensbi_path = Path("/home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi")
        
        if not cls.opensbi_path.exists():
            raise FileNotFoundError(f"OpenSBI代码路径不存在: {cls.opensbi_path}")
        
        # 创建真实解析器和存储
        cls.parser = CParser()
        cls.graph_store = Neo4jGraphStore()
        
        # 尝试连接Neo4j
        success = cls.graph_store.connect(
            uri="bolt://localhost:7687",
            user="neo4j",
            password=os.environ.get("NEO4J_PASSWORD", "password")
        )
        
        if not success:
            raise ConnectionError("无法连接到Neo4j数据库")
        
        # 创建依赖服务
        cls.dependency_service = DependencyService(
            parser=cls.parser,
            graph_store=cls.graph_store
        )
    
    @classmethod
    def tearDownClass(cls):
        """测试后清理"""
        # 关闭Neo4j连接
        if hasattr(cls, 'graph_store') and cls.graph_store:
            cls.graph_store.close()
    
    def test_opensbi_file_dependency_analysis(self):
        """测试OpenSBI文件依赖分析"""
        # 选择一个典型的OpenSBI源文件进行分析
        test_file = self.opensbi_path / "lib" / "sbi" / "sbi_init.c"
        
        if not test_file.exists():
            self.skipTest(f"测试文件不存在: {test_file}")
        
        # 分析文件依赖
        dependencies = self.dependency_service.analyze_file(test_file)
        
        # 验证依赖提取
        self.assertGreater(len(dependencies), 0, "应该提取到至少一个依赖关系")
        
        # 验证依赖类型
        system_deps = [dep for dep in dependencies if dep.is_system]
        project_deps = [dep for dep in dependencies if not dep.is_system]
        
        self.assertGreaterEqual(len(project_deps), 1, "应该至少有一个项目内部依赖")
        
        # 输出依赖信息
        print(f"\n文件 {test_file.name} 的依赖关系:")
        print(f"系统头文件: {len(system_deps)}个")
        print(f"项目头文件: {len(project_deps)}个")
        for i, dep in enumerate(project_deps[:5]):  # 只显示前5个
            print(f"{i+1}. {dep.target_file}")
    
    def test_opensbi_module_dependency_analysis(self):
        """测试OpenSBI模块依赖分析"""
        # 选择一个子目录进行分析
        test_dir = self.opensbi_path / "lib" / "sbi"
        
        if not test_dir.exists() or not test_dir.is_dir():
            self.skipTest(f"测试目录不存在: {test_dir}")
        
        # 分析项目依赖
        project_deps = self.dependency_service.analyze_project(test_dir)
        
        # 验证文件依赖
        self.assertGreater(len(project_deps.file_dependencies), 0, "应该提取到至少一个文件依赖关系")
        
        # 验证模块依赖
        self.assertGreaterEqual(len(project_deps.module_dependencies), 0, "应该提取到模块依赖关系")
        
        # 输出依赖统计
        stats = project_deps.get_stats()
        print("\n依赖关系统计:")
        print(f"文件依赖数: {stats['file_dependencies_count']}")
        print(f"模块依赖数: {stats['module_dependencies_count']}")
        print(f"循环依赖数: {stats['circular_dependencies_count']}")
        print(f"系统头文件数: {stats['system_headers_count']}")
        print(f"项目头文件数: {stats['project_headers_count']}")
        print(f"模块化评分: {stats['modularity_score']:.2f}/1.00")
        
        # 如果有循环依赖，输出警告
        if stats['circular_dependencies_count'] > 0:
            print("\n检测到循环依赖:")
            for i, cycle in enumerate(project_deps.circular_dependencies[:3]):  # 只显示前3个
                print(f"循环 {i+1}: {' -> '.join(cycle)}")
    
    def test_opensbi_dependency_graph_generation(self):
        """测试OpenSBI依赖图生成"""
        # 选择一个子目录进行分析
        test_dir = self.opensbi_path / "lib" / "sbi"
        
        if not test_dir.exists() or not test_dir.is_dir():
            self.skipTest(f"测试目录不存在: {test_dir}")
        
        # 先分析项目
        self.dependency_service.analyze_project(test_dir)
        
        # 生成模块依赖图（ASCII格式）
        module_graph = self.dependency_service.generate_dependency_graph(
            output_format="ascii",
            scope="module"
        )
        
        # 验证图内容
        self.assertIn("模块依赖关系:", module_graph)
        
        # 输出依赖图示例
        print("\n模块依赖图示例:")
        print(module_graph[:500] + "..." if len(module_graph) > 500 else module_graph)


if __name__ == "__main__":
    unittest.main() 