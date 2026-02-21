#!/usr/bin/env python3
"""
DAT - Digital Ark Tool
无U盘系统重装工具

入口文件
"""

import sys
import os

# 确保当前目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import is_admin, run_as_admin, logger
from config import APP_NAME, VERSION


def main():
    """程序主入口"""
    logger.info(f"启动 {APP_NAME} v{VERSION}")
    
    # 检查管理员权限
    if not is_admin():
        logger.info("请求管理员权限...")
        run_as_admin()
        return 0
    
    logger.info("已获得管理员权限")
    
    # 启动管理器
    try:
        from manager import Manager
        app = Manager()
        app.run()
    except Exception as e:
        logger.error(f"程序异常: {e}", exc_info=True)
        from utils import show_error_dialog
        show_error_dialog("DAT 错误", f"程序发生异常：\n{e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())