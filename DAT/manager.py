"""
DAT 主管理器
负责协调各模块的工作流程
"""

import sys
from utils import logger, show_error_dialog
from migration import MigrationWizard
from repository import Repository


class Manager:
    """主管理器类"""
    
    def __init__(self):
        self.locked = False  # 功能是否锁定（在系统盘运行时）
        self.repo = None
    
    def run(self):
        """运行主流程"""
        logger.info("开始运行主流程")
        
        # Step 1: 迁移检查
        result = self._handle_migration()
        if result is None:
            return
        
        # Step 2: 仓库检查/初始化
        if not self._handle_repository():
            return
        
        # Step 3: 启动主界面
        self._launch_ui()
    
    def _handle_migration(self):
        """处理迁移逻辑"""
        logger.info("检查程序位置...")
        
        wizard = MigrationWizard()
        result = wizard.run()
        
        if result == "no_disk":
            logger.error("没有可用的非系统盘")
            show_error_dialog(
                "DAT - 无法运行",
                "本程序需要至少一个未加密的非系统盘\n"
                "（可用空间至少 20GB）\n\n"
                "您的电脑当前不满足运行条件。"
            )
            sys.exit(1)
        
        if result == "migrated":
            # 迁移后会启动新程序，当前进程退出
            return None
        
        if result == "locked":
            logger.warning("用户选择在系统盘运行，功能已锁定")
            self.locked = True
        
        return result
    
    def _handle_repository(self):
        """处理仓库逻辑"""
        logger.info("检查仓库状态...")
        
        self.repo = Repository()
        
        if not self.repo.exists():
            logger.info("仓库不存在，开始初始化...")
            try:
                self.repo.initialize()
                logger.info("仓库初始化完成")
            except Exception as e:
                logger.error(f"仓库初始化失败: {e}")
                show_error_dialog("DAT 错误", f"仓库初始化失败：\n{e}")
                return False
        else:
            logger.info(f"找到仓库: {self.repo.root}")
        
        return True
    
    def _launch_ui(self):
        """启动用户界面"""
        logger.info("启动用户界面")
        
        from ui_desktop import DesktopUI
        ui = DesktopUI(repo=self.repo, locked=self.locked)
        ui.run()