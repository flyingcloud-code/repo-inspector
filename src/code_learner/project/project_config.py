"""
项目配置管理模块，负责读取和写入项目配置
"""
import os
import json
from typing import Dict, Any, Optional


class ProjectConfig:
    """
    项目配置管理类，负责读取和写入项目配置
    """
    
    # 默认配置
    DEFAULT_CONFIG = {
        "project_data_dir": "./data/projects",
        "default_project_id": None
    }
    
    def __init__(self, config_file: str = "./config/project_config.json"):
        """
        初始化项目配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = {}
        
        # 加载配置
        self._load_config()
        
    def _load_config(self) -> None:
        """
        加载配置文件，如果不存在则创建默认配置
        """
        # 如果配置文件存在，读取配置
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载配置文件失败: {e}")
                # 如果加载失败，使用默认配置
                self.config = self.DEFAULT_CONFIG.copy()
        else:
            # 如果配置文件不存在，使用默认配置
            self.config = self.DEFAULT_CONFIG.copy()
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            # 保存默认配置
            self.save()
            
    def save(self) -> None:
        """
        保存配置到文件
        """
        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # 写入配置文件
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存配置文件失败: {e}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            key: 配置项键名
            default: 默认值，如果配置项不存在则返回此值
            
        Returns:
            配置项值
        """
        return self.config.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """
        设置配置项
        
        Args:
            key: 配置项键名
            value: 配置项值
        """
        self.config[key] = value
        
    def reset(self) -> None:
        """
        重置配置为默认值
        """
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()
        
    def get_default_project_id(self) -> Optional[str]:
        """
        获取默认项目ID
        
        Returns:
            默认项目ID，如果未设置则返回None
        """
        return self.get("default_project_id")
        
    def set_default_project_id(self, project_id: str) -> None:
        """
        设置默认项目ID
        
        Args:
            project_id: 项目ID
        """
        self.set("default_project_id", project_id)
        self.save() 