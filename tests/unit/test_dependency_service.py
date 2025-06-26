import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
import os
import tempfile

from code_learner.llm.dependency_service import DependencyService
from code_learner.core.data_models import FileDependency, ModuleDependency, ProjectDependencies


class TestDependencyService(unittest.TestCase):
    """依赖分析服务单元测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建模拟解析器和图存储
        self.mock_parser = MagicMock()
        self.mock_graph_store = MagicMock()
        
        # 创建依赖分析服务
        self.service = DependencyService(
            parser=self.mock_parser,
            graph_store=self.mock_graph_store
        )
        
        # 创建测试数据
        self.test_file_deps = [
            FileDependency(
                source_file="/test/main.c",
                target_file="/test/utils.h",
                dependency_type="include",
                is_system=False,
                line_number=5,
                context='#include "utils.h"'
            ),
            FileDependency(
                source_file="/test/main.c",
                target_file="stdio.h",
                dependency_type="include",
                is_system=True,
                line_number=3,
                context='#include <stdio.h>'
            )
        ]
        
        self.test_module_deps = [
            ModuleDependency(
                source_module="main",
                target_module="utils",
                file_count=1,
                strength=0.5,
                is_circular=False,
                files=[("/test/main.c", "/test/utils.h")]
            )
        ]
        
        self.test_project_deps = ProjectDependencies(
            file_dependencies=self.test_file_deps,
            module_dependencies=self.test_module_deps,
            circular_dependencies=[],
            modularity_score=0.8
        )
    
    def test_analyze_project(self):
        """测试项目依赖分析"""
        # 设置模拟返回值
        self.mock_parser.analyze_project_dependencies.return_value = self.test_project_deps
        self.mock_graph_store.store_file_dependencies.return_value = True
        self.mock_graph_store.store_module_dependencies.return_value = True
        
        # 调用分析方法
        result = self.service.analyze_project("/test")
        
        # 验证结果
        self.assertEqual(result, self.test_project_deps)
        self.mock_parser.analyze_project_dependencies.assert_called_once_with(Path("/test"))
        self.mock_graph_store.store_file_dependencies.assert_called_once_with(self.test_file_deps)
        self.mock_graph_store.store_module_dependencies.assert_called_once_with(self.test_module_deps)
    
    def test_analyze_file(self):
        """测试文件依赖分析"""
        # 设置模拟返回值
        self.mock_parser.extract_file_dependencies.return_value = self.test_file_deps
        self.mock_graph_store.store_file_dependencies.return_value = True
        
        # 调用分析方法
        result = self.service.analyze_file("/test/main.c")
        
        # 验证结果
        self.assertEqual(result, self.test_file_deps)
        self.mock_parser.extract_file_dependencies.assert_called_once_with(Path("/test/main.c"))
        self.mock_graph_store.store_file_dependencies.assert_called_once_with(self.test_file_deps)
    
    def test_get_file_dependencies(self):
        """测试获取文件依赖关系"""
        # 设置模拟返回值
        expected_deps = [
            {
                "source_file": "/test/main.c",
                "target_file": "/test/utils.h",
                "dependency_type": "include",
                "is_system": False,
                "line_number": 5,
                "context": '#include "utils.h"'
            }
        ]
        self.mock_graph_store.query_file_dependencies.return_value = expected_deps
        
        # 调用方法
        result = self.service.get_file_dependencies("/test/main.c")
        
        # 验证结果
        self.assertEqual(result, expected_deps)
        self.mock_graph_store.query_file_dependencies.assert_called_once_with("/test/main.c")
    
    def test_get_module_dependencies(self):
        """测试获取模块依赖关系"""
        # 设置模拟返回值
        expected_deps = [
            {
                "source_module": "main",
                "target_module": "utils",
                "file_count": 1,
                "strength": 0.5,
                "is_circular": False,
                "files": [("/test/main.c", "/test/utils.h")]
            }
        ]
        self.mock_graph_store.query_module_dependencies.return_value = expected_deps
        
        # 调用方法
        result = self.service.get_module_dependencies("main")
        
        # 验证结果
        self.assertEqual(result, expected_deps)
        self.mock_graph_store.query_module_dependencies.assert_called_once_with("main")
    
    def test_get_circular_dependencies(self):
        """测试获取循环依赖"""
        # 设置模拟返回值
        expected_cycles = [["main", "utils", "common", "main"]]
        self.mock_graph_store.detect_circular_dependencies.return_value = expected_cycles
        
        # 调用方法
        result = self.service.get_circular_dependencies()
        
        # 验证结果
        self.assertEqual(result, expected_cycles)
        self.mock_graph_store.detect_circular_dependencies.assert_called_once()
    
    def test_generate_dependency_graph_file_json(self):
        """测试生成文件依赖图（JSON格式）"""
        # 设置模拟返回值
        file_deps = [
            {
                "source_file": "/test/main.c",
                "target_file": "/test/utils.h",
                "dependency_type": "include",
                "is_system": False,
                "line_number": 5,
                "context": '#include "utils.h"'
            }
        ]
        self.mock_graph_store.query_file_dependencies.return_value = file_deps
        
        # 调用方法
        result = self.service.generate_dependency_graph(
            output_format="json",
            scope="file",
            focus_item="/test/main.c"
        )
        
        # 验证结果
        self.assertIn('"source_file": "/test/main.c"', result)
        self.assertIn('"target_file": "/test/utils.h"', result)
        self.mock_graph_store.query_file_dependencies.assert_called_once_with("/test/main.c")
    
    def test_generate_dependency_graph_module_mermaid(self):
        """测试生成模块依赖图（Mermaid格式）"""
        # 设置模拟返回值
        module_deps = [
            {
                "source_module": "main",
                "target_module": "utils",
                "file_count": 1,
                "strength": 0.5,
                "is_circular": False,
                "files": [("/test/main.c", "/test/utils.h")]
            }
        ]
        self.mock_graph_store.query_module_dependencies.return_value = module_deps
        
        # 调用方法
        result = self.service.generate_dependency_graph(
            output_format="mermaid",
            scope="module"
        )
        
        # 验证结果
        self.assertIn("graph LR", result)
        self.assertIn("-->|1文件|", result)
        self.assertIn("main", result)
        self.assertIn("utils", result)
        self.mock_graph_store.query_module_dependencies.assert_called_once_with(None)
    
    def test_generate_dependency_graph_empty(self):
        """测试生成空依赖图"""
        # 设置模拟返回值
        self.mock_graph_store.query_file_dependencies.return_value = []
        
        # 调用方法
        result = self.service.generate_dependency_graph(scope="file")
        
        # 验证结果
        self.assertEqual(result, "没有找到依赖关系")
    
    def test_generate_dependency_graph_invalid_format(self):
        """测试无效的输出格式"""
        # 设置模拟返回值
        module_deps = [
            {
                "source_module": "main",
                "target_module": "utils",
                "file_count": 1,
                "strength": 0.5,
                "is_circular": False,
                "files": []
            }
        ]
        self.mock_graph_store.query_module_dependencies.return_value = module_deps
        
        # 验证异常
        with self.assertRaises(ValueError):
            self.service.generate_dependency_graph(
                output_format="invalid",
                scope="module"
            )
    
    def test_generate_dependency_graph_invalid_scope(self):
        """测试无效的依赖范围"""
        # 验证异常
        with self.assertRaises(ValueError):
            self.service.generate_dependency_graph(scope="invalid")


if __name__ == "__main__":
    unittest.main() 