"""
项目管理器模块，负责项目的创建、获取、列表和删除等功能
"""
import os
import json
import hashlib
import datetime
from typing import Dict, List, Optional, Any


class ProjectManager:
    """
    项目管理器类，负责管理项目元数据和项目隔离
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化项目管理器
        
        Args:
            config: 配置字典，必须包含project_data_dir键
        """
        self.config = config
        self.project_data_dir = config.get("project_data_dir", "./data/projects")
        
        # 确保项目数据目录存在
        os.makedirs(self.project_data_dir, exist_ok=True)
        
    def create_project(self, repo_path: str, name: Optional[str] = None) -> str:
        """
        创建新项目或获取现有项目
        
        Args:
            repo_path: 代码仓库路径
            name: 项目名称，如果不指定则使用仓库名称
            
        Returns:
            项目ID
        """
        # 生成项目ID
        project_id = self._generate_project_id(repo_path)
        
        # 如果项目已存在，直接返回ID
        if self.project_exists(project_id):
            return project_id
        
        # 如果未指定名称，使用仓库名称
        if name is None:
            name = os.path.basename(os.path.abspath(repo_path))
            
        # 创建项目元数据
        project_data = {
            "id": project_id,
            "name": name,
            "repo_path": repo_path,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        # 存储项目元数据
        self._store_project_metadata(project_id, project_data)
        
        return project_id
        
    def get_project(self, project_id: Optional[str] = None, repo_path: Optional[str] = None) -> Dict[str, Any]:
        """
        获取项目信息
        
        Args:
            project_id: 项目ID
            repo_path: 代码仓库路径
            
        Returns:
            项目元数据字典
            
        Raises:
            ValueError: 如果项目不存在或者未提供ID和路径
        """
        # 如果提供了仓库路径，根据路径获取项目ID
        if repo_path is not None:
            project_id = self._generate_project_id(repo_path)
            
        # 如果没有提供ID和路径，抛出异常
        if project_id is None:
            raise ValueError("必须提供project_id或repo_path参数")
            
        # 获取项目元数据
        project_file = os.path.join(self.project_data_dir, f"{project_id}.json")
        
        # 如果项目文件不存在，抛出异常
        if not os.path.exists(project_file):
            raise ValueError(f"项目 {project_id} 不存在")
            
        # 读取项目元数据
        with open(project_file, "r", encoding="utf-8") as f:
            return json.load(f)
        
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        列出所有项目
        
        Returns:
            项目元数据字典列表
        """
        projects = []
        
        # 遍历项目数据目录
        for filename in os.listdir(self.project_data_dir):
            if filename.endswith(".json"):
                # 读取项目元数据
                project_file = os.path.join(self.project_data_dir, filename)
                with open(project_file, "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                    projects.append(project_data)
                    
        return projects
        
    def delete_project(self, project_id: str) -> None:
        """
        删除项目
        
        Args:
            project_id: 项目ID
            
        Raises:
            ValueError: 如果项目不存在
        """
        # 检查项目是否存在
        if not self.project_exists(project_id):
            raise ValueError(f"项目 {project_id} 不存在")
            
        # 删除项目元数据文件
        project_file = os.path.join(self.project_data_dir, f"{project_id}.json")
        os.remove(project_file)
        
    def project_exists(self, project_id: str) -> bool:
        """
        检查项目是否存在
        
        Args:
            project_id: 项目ID
            
        Returns:
            项目是否存在
        """
        project_file = os.path.join(self.project_data_dir, f"{project_id}.json")
        return os.path.exists(project_file)
        
    def _generate_project_id(self, repo_path: str) -> str:
        """
        根据仓库路径生成唯一项目ID
        
        Args:
            repo_path: 代码仓库路径
            
        Returns:
            项目ID（以p开头，后跟10个字符的哈希值）
        """
        # 使用绝对路径生成哈希值
        abs_path = os.path.abspath(repo_path)
        return "p" + hashlib.md5(abs_path.encode()).hexdigest()[:10]
        
    def _store_project_metadata(self, project_id: str, project_data: Dict[str, Any]) -> None:
        """
        存储项目元数据
        
        Args:
            project_id: 项目ID
            project_data: 项目元数据字典
        """
        # 确保项目数据目录存在
        os.makedirs(self.project_data_dir, exist_ok=True)
        
        # 写入项目元数据文件
        project_file = os.path.join(self.project_data_dir, f"{project_id}.json")
        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        
    def _create_project_config(self, repo_path: str, project_name: str, project_id: str) -> None:
        """
        使用指定的项目ID创建项目配置
        
        Args:
            repo_path: 代码仓库路径
            project_name: 项目名称
            project_id: 项目ID
        """
        # 创建项目元数据
        project_data = {
            "id": project_id,
            "name": project_name,
            "repo_path": repo_path,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        # 存储项目元数据
        self._store_project_metadata(project_id, project_data) 