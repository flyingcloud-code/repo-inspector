import os
import unittest
import tempfile
import json
import shutil
from unittest.mock import patch, MagicMock

from src.code_learner.project.project_config import ProjectConfig


class TestProjectConfig(unittest.TestCase):
    def setUp(self):
        # 创建临时目录作为测试配置目录
        self.test_config_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.test_config_dir, "config.json")
        
    def tearDown(self):
        # 清理临时目录
        shutil.rmtree(self.test_config_dir)
        
    def test_init_default_config(self):
        """测试初始化默认配置"""
        # 创建配置对象，不存在配置文件时应创建默认配置
        config = ProjectConfig(self.config_file)
        
        # 验证默认配置
        self.assertEqual(config.get("project_data_dir"), "./data/projects")
        self.assertIsNone(config.get("default_project_id"))
        
        # 验证配置文件已创建
        self.assertTrue(os.path.exists(self.config_file))
        
    def test_load_existing_config(self):
        """测试加载现有配置"""
        # 创建测试配置文件
        test_config = {
            "project_data_dir": "/custom/data/dir",
            "default_project_id": "p1234567890"
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(test_config, f)
            
        # 加载配置
        config = ProjectConfig(self.config_file)
        
        # 验证配置已正确加载
        self.assertEqual(config.get("project_data_dir"), "/custom/data/dir")
        self.assertEqual(config.get("default_project_id"), "p1234567890")
        
    def test_save_config(self):
        """测试保存配置"""
        # 创建配置对象
        config = ProjectConfig(self.config_file)
        
        # 修改配置
        config.set("project_data_dir", "/new/data/dir")
        config.set("default_project_id", "p9876543210")
        
        # 保存配置
        config.save()
        
        # 重新加载配置
        new_config = ProjectConfig(self.config_file)
        
        # 验证配置已正确保存
        self.assertEqual(new_config.get("project_data_dir"), "/new/data/dir")
        self.assertEqual(new_config.get("default_project_id"), "p9876543210")
        
    def test_get_default_project(self):
        """测试获取默认项目"""
        # 创建配置对象
        config = ProjectConfig(self.config_file)
        
        # 初始状态应该没有默认项目
        self.assertIsNone(config.get_default_project_id())
        
        # 设置默认项目
        config.set_default_project_id("p1234567890")
        
        # 验证默认项目已设置
        self.assertEqual(config.get_default_project_id(), "p1234567890")
        
        # 验证配置已保存
        new_config = ProjectConfig(self.config_file)
        self.assertEqual(new_config.get_default_project_id(), "p1234567890")
        
    def test_reset_config(self):
        """测试重置配置"""
        # 创建配置对象并修改
        config = ProjectConfig(self.config_file)
        config.set("project_data_dir", "/custom/data/dir")
        config.set("default_project_id", "p1234567890")
        config.save()
        
        # 重置配置
        config.reset()
        
        # 验证配置已重置为默认值
        self.assertEqual(config.get("project_data_dir"), "./data/projects")
        self.assertIsNone(config.get("default_project_id"))
        
        # 验证配置文件已更新
        new_config = ProjectConfig(self.config_file)
        self.assertEqual(new_config.get("project_data_dir"), "./data/projects")
        self.assertIsNone(new_config.get("default_project_id"))


if __name__ == "__main__":
    unittest.main() 