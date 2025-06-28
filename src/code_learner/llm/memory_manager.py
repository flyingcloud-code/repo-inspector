"""
内存管理器

负责监控系统内存使用情况并提供内存优化建议。
遵循单一职责原则，专注于内存管理。
"""
import gc
import psutil
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """内存使用统计"""
    percent_used: float
    available_gb: float
    total_gb: float


class MemoryManager:
    """内存管理器
    
    专门负责内存监控、清理和批次大小建议。
    遵循单一职责原则。
    """
    
    def __init__(self, max_memory_percent: float = 80.0):
        """初始化内存管理器
        
        Args:
            max_memory_percent: 最大内存使用百分比阈值
        """
        self.max_memory_percent = max_memory_percent
        logger.info(f"内存管理器初始化: 最大内存使用 {max_memory_percent}%")
    
    def get_memory_stats(self) -> MemoryStats:
        """获取当前内存使用统计"""
        memory = psutil.virtual_memory()
        return MemoryStats(
            percent_used=memory.percent,
            available_gb=memory.available / (1024**3),
            total_gb=memory.total / (1024**3)
        )
    
    def is_memory_pressure_high(self) -> bool:
        """检查是否存在内存压力"""
        return self.get_memory_stats().percent_used > self.max_memory_percent
    
    def suggest_batch_size_reduction(self, current_batch_size: int) -> Optional[int]:
        """建议批次大小减少
        
        Args:
            current_batch_size: 当前批次大小
            
        Returns:
            建议的新批次大小，如果不需要调整则返回None
        """
        if self.is_memory_pressure_high():
            new_size = max(5, current_batch_size // 2)
            if new_size != current_batch_size:
                memory_stats = self.get_memory_stats()
                logger.warning(f"内存压力过高({memory_stats.percent_used:.1f}%)，建议减少批次大小: {current_batch_size} -> {new_size}")
                return new_size
        return None
    
    def cleanup_memory(self) -> None:
        """执行内存清理"""
        gc.collect()
        
        # 如果使用GPU，也清理GPU内存
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
    
    def log_memory_usage(self, stage: str) -> None:
        """记录内存使用情况（简化版本）"""
        if logger.isEnabledFor(logging.INFO):
            memory_stats = self.get_memory_stats()
            logger.info(f"[{stage}] 内存: {memory_stats.percent_used:.1f}%, 可用: {memory_stats.available_gb:.1f}GB") 