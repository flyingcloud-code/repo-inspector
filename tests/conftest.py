"""pytest 全局配置
确保项目根目录加入 PYTHONPATH，便于 'src.*' 导入
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT)) 