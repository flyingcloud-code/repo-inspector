"""
CLI辅助函数模块
"""

def confirm_action(prompt: str) -> bool:
    """
    向用户显示一个提示，并要求他们确认操作。

    Args:
        prompt: 显示给用户的确认问题。

    Returns:
        bool: 如果用户确认则返回True，否则返回False。
    """
    while True:
        response = input(f"{prompt} [y/N]: ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no', '']:
            return False
        else:
            print("无效输入，请输入 'y' 或 'n'。") 