#!/usr/bin/env python3
"""
Qwen3模型依赖检查脚本

快速检查系统是否满足Qwen3-Embedding-0.6B模型的运行要求
"""

def check_dependencies():
    """检查依赖库和版本要求"""
    print("🔍 检查Qwen3-Embedding-0.6B模型依赖...")
    print("=" * 50)
    
    # 检查Python版本
    import sys
    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    if python_version >= (3, 8):
        print("✅ Python版本满足要求 (>=3.8)")
    else:
        print("❌ Python版本过低，需要>=3.8")
    
    # 检查各个库
    libraries = [
        ("sentence-transformers", "2.7.0", "用于简单的模型加载和使用"),
        ("transformers", "4.51.0", "Qwen3模型的最低要求版本"),
        ("torch", "2.0.0", "PyTorch深度学习框架"),
        ("numpy", "1.20.0", "数值计算库")
    ]
    
    results = {}
    
    for lib_name, min_version, description in libraries:
        try:
            lib = __import__(lib_name)
            version = getattr(lib, '__version__', 'unknown')
            results[lib_name] = {
                'installed': True,
                'version': version,
                'description': description,
                'meets_requirement': version >= min_version if version != 'unknown' else False
            }
            
            status = "✅" if results[lib_name]['meets_requirement'] else "⚠️"
            print(f"{status} {lib_name}: {version} (需要>={min_version}) - {description}")
            
        except ImportError:
            results[lib_name] = {
                'installed': False,
                'version': None,
                'description': description,
                'meets_requirement': False
            }
            print(f"❌ {lib_name}: 未安装 (需要>={min_version}) - {description}")
    
    print("\n" + "=" * 50)
    
    # 总结
    all_installed = all(r['installed'] for r in results.values())
    all_meet_requirements = all(r['meets_requirement'] for r in results.values())
    
    if all_installed and all_meet_requirements:
        print("🎉 所有依赖都满足要求，可以开始Qwen3模型测试！")
        return True
    elif all_installed:
        print("⚠️ 所有库都已安装，但部分版本可能过低")
        print("建议升级：pip install --upgrade transformers sentence-transformers")
        return False
    else:
        print("❌ 部分依赖缺失，需要安装")
        missing = [name for name, result in results.items() if not result['installed']]
        print(f"安装命令：pip install {' '.join(missing)}")
        return False

if __name__ == "__main__":
    check_dependencies() 