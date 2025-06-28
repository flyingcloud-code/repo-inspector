import os
import unittest
import tempfile
import json
import shutil
from unittest.mock import patch, MagicMock

from src.code_learner.project.project_manager import ProjectManager


class TestProjectManager(unittest.TestCase):
    def setUp(self):
        # 创建临时目录作为测试数据目录
        self.test_data_dir = tempfile.mkdtemp()
        self.config = {
            "project_data_dir": self.test_data_dir
        }
        self.project_manager = ProjectManager(self.config)
        
    def tearDown(self):
        # 清理临时目录
        shutil.rmtree(self.test_data_dir)
        
    def test_generate_project_id(self):
        """测试项目ID生成算法"""
        # 同一路径应该生成相同的ID
        path1 = "/path/to/repo"
        path2 = "/path/to/repo"
        path3 = "/different/path"
        
        id1 = self.project_manager._generate_project_id(path1)
        id2 = self.project_manager._generate_project_id(path2)
        id3 = self.project_manager._generate_project_id(path3)
        
        # 检查ID格式是否正确（以p开头，后跟10个字符）
        self.assertTrue(id1.startswith("p"))
        self.assertEqual(len(id1), 11)
        
        # 相同路径生成相同ID
        self.assertEqual(id1, id2)
        
        # 不同路径生成不同ID
        self.assertNotEqual(id1, id3)
        
    def test_create_project(self):
        """测试项目创建功能"""
        repo_path = "/path/to/test/repo"
        project_name = "Test Project"
        
        # 创建项目
        project_id = self.project_manager.create_project(repo_path, project_name)
        
        # 验证项目ID格式
        self.assertTrue(project_id.startswith("p"))
        self.assertEqual(len(project_id), 11)
        
        # 验证项目元数据是否正确存储
        project_data = self.project_manager.get_project(project_id)
        self.assertEqual(project_data["name"], project_name)
        self.assertEqual(project_data["repo_path"], repo_path)
        self.assertTrue("created_at" in project_data)
        
        # 测试不指定名称时使用仓库名
        repo_path2 = "/path/to/another/repo"
        project_id2 = self.project_manager.create_project(repo_path2)
        project_data2 = self.project_manager.get_project(project_id2)
        self.assertEqual(project_data2["name"], "repo")  # 从路径中提取的名称
        
    def test_get_project(self):
        """测试获取项目信息功能"""
        # 创建测试项目
        repo_path = "/path/to/repo"
        project_name = "Test Project"
        project_id = self.project_manager.create_project(repo_path, project_name)
        
        # 通过ID获取项目
        project_data = self.project_manager.get_project(project_id=project_id)
        self.assertEqual(project_data["name"], project_name)
        self.assertEqual(project_data["repo_path"], repo_path)
        
        # 通过路径获取项目
        project_data = self.project_manager.get_project(repo_path=repo_path)
        self.assertEqual(project_data["id"], project_id)
        self.assertEqual(project_data["name"], project_name)
        
        # 获取不存在的项目
        with self.assertRaises(ValueError):
            self.project_manager.get_project(project_id="non_existent_id")
            
        # 不提供ID或路径
        with self.assertRaises(ValueError):
            self.project_manager.get_project()
            
    def test_list_projects(self):
        """测试项目列表功能"""
        # 初始状态应该没有项目
        projects = self.project_manager.list_projects()
        self.assertEqual(len(projects), 0)
        
        # 创建多个项目
        project_id1 = self.project_manager.create_project("/path/to/repo1", "Project 1")
        project_id2 = self.project_manager.create_project("/path/to/repo2", "Project 2")
        project_id3 = self.project_manager.create_project("/path/to/repo3", "Project 3")
        
        # 获取项目列表
        projects = self.project_manager.list_projects()
        
        # 验证列表长度和内容
        self.assertEqual(len(projects), 3)
        project_ids = [p["id"] for p in projects]
        self.assertIn(project_id1, project_ids)
        self.assertIn(project_id2, project_ids)
        self.assertIn(project_id3, project_ids)
        
    def test_delete_project(self):
        """测试删除项目功能"""
        # 创建测试项目
        project_id = self.project_manager.create_project("/path/to/repo", "Test Project")
        
        # 确认项目存在
        self.assertTrue(self.project_manager.project_exists(project_id))
        
        # 删除项目
        self.project_manager.delete_project(project_id)
        
        # 确认项目已删除
        self.assertFalse(self.project_manager.project_exists(project_id))
        
        # 尝试删除不存在的项目
        with self.assertRaises(ValueError):
            self.project_manager.delete_project("non_existent_id")
            
    def test_project_exists(self):
        """测试项目存在性检查功能"""
        # 创建测试项目
        project_id = self.project_manager.create_project("/path/to/repo", "Test Project")
        
        # 检查存在性
        self.assertTrue(self.project_manager.project_exists(project_id))
        self.assertFalse(self.project_manager.project_exists("non_existent_id"))


if __name__ == "__main__":
    unittest.main() 