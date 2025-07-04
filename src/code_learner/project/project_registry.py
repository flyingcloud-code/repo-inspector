"""
项目注册表模块

管理用户的项目注册表 (~/.code_learner/projects.json)
实现项目的创建、列表、删除和查找功能
"""

import os
import json
import hashlib
import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class ProjectRegistry:
    """
    项目注册表类，管理项目的生命周期
    """
    
    def __init__(self):
        """初始化项目注册表"""
        self.registry_dir = Path.home() / ".code_learner"
        self.registry_file = self.registry_dir / "projects.json"
        
        # 确保注册表目录存在
        self.registry_dir.mkdir(exist_ok=True)
        
        # 如果注册表文件不存在，创建空的注册表
        if not self.registry_file.exists():
            self._create_empty_registry()
    
    def _create_empty_registry(self):
        """创建空的项目注册表"""
        empty_registry = {"projects": []}
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(empty_registry, f, ensure_ascii=False, indent=2)
    
    def _load_registry(self) -> Dict[str, Any]:
        """加载项目注册表"""
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # 如果文件损坏或不存在，创建新的空注册表
            self._create_empty_registry()
            return {"projects": []}
    
    def _save_registry(self, registry: Dict[str, Any]):
        """保存项目注册表"""
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
    
    def _generate_project_id(self, project_path: str) -> str:
        """
        根据项目路径生成唯一项目ID
        
        Args:
            project_path: 项目路径
            
        Returns:
            项目ID（格式：auto_xxxxxxxx）
        """
        abs_path = os.path.abspath(project_path)
        return "auto_" + hashlib.md5(abs_path.encode()).hexdigest()[:8]
    
    def create_project(self, project_path: str, name: str) -> Dict[str, Any]:
        """
        创建新项目
        
        Args:
            project_path: 项目路径
            name: 项目短名称
            
        Returns:
            Dict[str, Any]: 创建的项目信息
            
        Raises:
            ValueError: 如果项目路径不存在或名称已被使用
        """
        # 验证项目路径
        if not os.path.exists(project_path):
            raise ValueError(f"项目路径不存在: {project_path}")
        
        # 生成项目ID
        project_id = self._generate_project_id(project_path)
        abs_path = os.path.abspath(project_path)
        
        # 加载注册表
        registry = self._load_registry()
        
        # 检查名称是否已被使用
        for project in registry["projects"]:
            if project["name"] == name:
                raise ValueError(f"项目名称 '{name}' 已被使用")
        
        # 检查项目是否已存在（基于路径）
        for project in registry["projects"]:
            if project["path"] == abs_path:
                raise ValueError(f"项目路径 '{abs_path}' 已被注册为 '{project['name']}'")
        
        # 创建项目信息
        project_info = {
            "name": name,
            "id": project_id,
            "path": abs_path,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        # 添加到注册表
        registry["projects"].append(project_info)
        
        # 保存注册表
        self._save_registry(registry)
        
        return project_info
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        列出所有项目
        
        Returns:
            List[Dict[str, Any]]: 项目列表
        """
        registry = self._load_registry()
        return registry["projects"]
    
    def find_project(self, name_or_id: str) -> Optional[Dict[str, Any]]:
        """
        根据名称或ID查找项目
        
        Args:
            name_or_id: 项目名称或ID
            
        Returns:
            Optional[Dict[str, Any]]: 项目信息，如果未找到返回None
        """
        registry = self._load_registry()
        
        for project in registry["projects"]:
            if project["name"] == name_or_id or project["id"] == name_or_id:
                return project
        
        return None
    
    def find_project_by_path(self, project_path: str) -> Optional[Dict[str, Any]]:
        """
        根据路径查找项目
        
        Args:
            project_path: 项目路径
            
        Returns:
            Optional[Dict[str, Any]]: 项目信息，如果未找到返回None
        """
        abs_path = os.path.abspath(project_path)
        registry = self._load_registry()
        
        for project in registry["projects"]:
            if project["path"] == abs_path:
                return project
        
        return None
    
    def delete_project(self, name_or_id: str) -> Dict[str, Any]:
        """
        删除项目
        
        Args:
            name_or_id: 项目名称或ID
            
        Returns:
            Dict[str, Any]: 被删除的项目信息
            
        Raises:
            ValueError: 如果项目不存在
        """
        registry = self._load_registry()
        
        # 查找要删除的项目
        project_to_delete = None
        project_index = -1
        
        for i, project in enumerate(registry["projects"]):
            if project["name"] == name_or_id or project["id"] == name_or_id:
                project_to_delete = project
                project_index = i
                break
        
        if project_to_delete is None:
            raise ValueError(f"项目 '{name_or_id}' 不存在")
        
        # 从注册表中移除
        registry["projects"].pop(project_index)
        
        # 保存注册表
        self._save_registry(registry)
        
        return project_to_delete
    
    def update_project(self, name_or_id: str, **kwargs) -> Dict[str, Any]:
        """
        更新项目信息
        
        Args:
            name_or_id: 项目名称或ID
            **kwargs: 要更新的字段
            
        Returns:
            Dict[str, Any]: 更新后的项目信息
            
        Raises:
            ValueError: 如果项目不存在
        """
        registry = self._load_registry()
        
        # 查找要更新的项目
        project_to_update = None
        project_index = -1
        
        for i, project in enumerate(registry["projects"]):
            if project["name"] == name_or_id or project["id"] == name_or_id:
                project_to_update = project
                project_index = i
                break
        
        if project_to_update is None:
            raise ValueError(f"项目 '{name_or_id}' 不存在")
        
        # 更新字段
        for key, value in kwargs.items():
            if key in ["name", "path"]:  # 只允许更新这些字段
                project_to_update[key] = value
        
        # 更新时间戳
        project_to_update["updated_at"] = datetime.datetime.now().isoformat()
        
        # 保存注册表
        self._save_registry(registry)
        
        return project_to_update
    
    def project_exists(self, name_or_id: str) -> bool:
        """
        检查项目是否存在
        
        Args:
            name_or_id: 项目名称或ID
            
        Returns:
            bool: 项目是否存在
        """
        return self.find_project(name_or_id) is not None 