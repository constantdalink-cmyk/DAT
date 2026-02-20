"""
DAT 迁移向导
负责检测程序位置并引导用户迁移到安全位置
"""

import os
import sys
import shutil
import subprocess
import psutil
import time

from utils import logger, get_system_drive
from config import MIN_FREE_SPACE_GB


class MigrationWizard:
    """迁移向导类"""
    
    def __init__(self):
        # 获取项目目录（main.py 所在目录）
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
    
    def run(self):
        """
        运行迁移向导
        返回值:
            'safe'     - 程序已在安全位置
            'migrated' - 已完成迁移（进程将退出）
            'locked'   - 用户选择继续在系统盘运行
            'no_disk'  - 没有可用的安全磁盘
        """
        logger.info("运行迁移向导")
        
        # 检查是否在系统盘
        if not self._is_on_system_drive():
            logger.info("程序已在非系统盘，无需迁移")
            return "safe"
        
        logger.warning("程序在系统盘运行")
        
        # 查找可用的安全磁盘
        target = self._find_safe_drive()
        if target is None:
            logger.error("未找到可用的安全磁盘")
            return "no_disk"
        
        logger.info(f"找到可用磁盘: {target}")
        
        # 第一层弹窗：迁移提示
        choice = self._show_migration_dialog(target)
        
        if choice == "migrate":
            logger.info("用户选择迁移")
            self._do_migration(target)
            return "migrated"
        
        # 第二层弹窗：风险确认
        confirm = self._show_risk_dialog()
        
        if confirm == "go_back":
            return self.run()
        
        return "locked"
    
    def _is_on_system_drive(self):
        """检查项目是否在系统盘"""
        current_drive = os.path.splitdrive(self.project_dir)[0].upper().rstrip(':')
        system_drive = get_system_drive()
        return current_drive == system_drive
    
    def _find_safe_drive(self):
        """查找安全的非系统磁盘"""
        system_drive = get_system_drive()
        candidates = []
        
        for part in psutil.disk_partitions():
            drive = part.device[0].upper()
            
            if drive == system_drive:
                continue
            
            if 'removable' in part.opts.lower():
                continue
            
            if 'cdrom' in part.opts.lower():
                continue
            
            try:
                usage = psutil.disk_usage(part.mountpoint)
                
                if usage.free < MIN_FREE_SPACE_GB * 1024**3:
                    logger.debug(f"{drive}: 空间不足，跳过")
                    continue
                
                if self._is_bitlocked(drive):
                    logger.debug(f"{drive}: 已加密，跳过")
                    continue
                
                candidates.append({
                    'drive': drive,
                    'free': usage.free,
                    'total': usage.total
                })
                
            except Exception as e:
                logger.debug(f"{drive}: 无法访问 - {e}")
                continue
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x['free'], reverse=True)
        return candidates[0]['drive']
    
    def _is_bitlocked(self, drive):
        """检查磁盘是否被 BitLocker 加密"""
        try:
            result = subprocess.run(
                ['manage-bde', '-status', f'{drive}:'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return 'Protection On' in result.stdout or '保护已打开' in result.stdout
        except Exception:
            return False
    
    def _do_migration(self, target_drive):
        """执行迁移操作"""
        # 源目录：项目所在目录
        source = self.project_dir
        # 目标目录
        target = f"{target_drive}:\\DAT"
        
        logger.info(f"迁移: {source} -> {target}")
        
        # 如果目标已存在，尝试删除
        if os.path.exists(target):
            logger.info("删除旧的目标目录")
            try:
                shutil.rmtree(target, ignore_errors=True)
            except Exception as e:
                logger.warning(f"无法完全删除旧目录: {e}")
            
            # 如果还存在，尝试重命名
            if os.path.exists(target):
                try:
                    backup_name = f"{target}_old_{int(time.time())}"
                    os.rename(target, backup_name)
                    logger.info(f"旧目录已重命名为: {backup_name}")
                except Exception as e:
                    logger.error(f"无法处理旧目录: {e}")
                    raise Exception(
                        f"目标目录 {target} 已存在且无法删除。\n"
                        f"请手动删除后重试。"
                    )
        
        # 复制项目文件
        logger.info("复制文件...")
        shutil.copytree(source, target)
        
        # 创建桌面快捷方式
        self._create_shortcut(target)
        
        # 启动新程序
        logger.info("启动迁移后的程序...")
        new_main = os.path.join(target, "main.py")
        
        subprocess.Popen(
            [sys.executable, new_main],
            cwd=target,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        # 退出当前进程
        sys.exit(0)
    
    def _create_shortcut(self, target_dir):
        """创建桌面快捷方式"""
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        shortcut = os.path.join(desktop, 'DAT.lnk')
        
        # 快捷方式目标：运行 main.py
        target_script = os.path.join(target_dir, 'main.py')
        
        ps_script = f'''
$s = (New-Object -COM WScript.Shell).CreateShortcut("{shortcut}")
$s.TargetPath = "{sys.executable}"
$s.Arguments = '"{target_script}"'
$s.WorkingDirectory = "{target_dir}"
$s.Description = "DAT - 数字方舟"
$s.Save()
'''
        try:
            subprocess.run(
                ['powershell', '-Command', ps_script],
                capture_output=True,
                timeout=10
            )
            logger.info(f"快捷方式已创建: {shortcut}")
        except Exception as e:
            logger.warning(f"创建快捷方式失败: {e}")
    
    def _show_migration_dialog(self, target_drive):
        """显示迁移提示对话框"""
        import customtkinter as ctk
        
        result = {"value": None}
        
        ctk.set_appearance_mode("dark")
        
        dialog = ctk.CTk()
        dialog.title("DAT")
        dialog.geometry("480x300")
        dialog.resizable(False, False)
        self._center_window(dialog, 480, 300)
        
        ctk.CTkLabel(
            dialog,
            text="⚠️ 检测到程序位于系统盘 (C:)",
            font=("Microsoft YaHei", 18, "bold")
        ).pack(pady=(35, 15))
        
        ctk.CTkLabel(
            dialog,
            text="为确保系统崩溃时本程序仍能工作，\n建议将程序迁移到其他磁盘。",
            font=("Microsoft YaHei", 13),
            justify="center"
        ).pack(pady=15)
        
        ctk.CTkLabel(
            dialog,
            text=f"目标位置：{target_drive}:\\DAT\\",
            font=("Microsoft YaHei", 12),
            text_color="gray"
        ).pack(pady=10)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=25)
        
        def on_migrate():
            result["value"] = "migrate"
            dialog.destroy()
        
        def on_skip():
            result["value"] = "skip"
            dialog.destroy()
        
        ctk.CTkButton(
            btn_frame,
            text="✓ 立即迁移",
            width=150,
            height=40,
            font=("Microsoft YaHei", 14),
            command=on_migrate
        ).pack(side="left", padx=15)
        
        ctk.CTkButton(
            btn_frame,
            text="暂不迁移",
            width=150,
            height=40,
            font=("Microsoft YaHei", 14),
            fg_color="gray",
            hover_color="darkgray",
            command=on_skip
        ).pack(side="left", padx=15)
        
        dialog.protocol("WM_DELETE_WINDOW", on_skip)
        dialog.mainloop()
        
        return result["value"]
    
    def _show_risk_dialog(self):
        """显示风险确认对话框"""
        import customtkinter as ctk
        
        result = {"value": None}
        
        dialog = ctk.CTk()
        dialog.title("DAT - 风险确认")
        dialog.geometry("500x380")
        dialog.resizable(False, False)
        self._center_window(dialog, 500, 380)
        
        ctk.CTkLabel(
            dialog,
            text="⚠️ 二次确认",
            font=("Microsoft YaHei", 18, "bold"),
            text_color="orange"
        ).pack(pady=(30, 15))
        
        ctk.CTkLabel(
            dialog,
            text="您确定要继续在系统盘运行吗？\n这样做可能导致：",
            font=("Microsoft YaHei", 13)
        ).pack(pady=10)
        
        risk_frame = ctk.CTkFrame(dialog)
        risk_frame.pack(pady=15, padx=40, fill="x")
        
        risk_text = (
            "❌ 程序\"自杀\"\n"
            "     重装系统时，程序会被一起清除，\n"
            "     导致无法完成后续安装步骤\n\n"
            "❌ 无法进行紧急修复\n"
            "     系统崩溃后，救援功能彻底失效"
        )
        
        ctk.CTkLabel(
            risk_frame,
            text=risk_text,
            font=("Microsoft YaHei", 12),
            justify="left"
        ).pack(padx=20, pady=20, anchor="w")
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=25)
        
        def on_confirm():
            result["value"] = "confirm"
            dialog.destroy()
        
        def on_back():
            result["value"] = "go_back"
            dialog.destroy()
        
        ctk.CTkButton(
            btn_frame,
            text="← 返回迁移",
            width=150,
            height=40,
            font=("Microsoft YaHei", 14),
            command=on_back
        ).pack(side="left", padx=15)
        
        ctk.CTkButton(
            btn_frame,
            text="我已了解风险",
            width=150,
            height=40,
            font=("Microsoft YaHei", 14),
            fg_color="darkred",
            hover_color="red",
            command=on_confirm
        ).pack(side="left", padx=15)
        
        dialog.protocol("WM_DELETE_WINDOW", on_back)
        dialog.mainloop()
        
        return result["value"]
    
    def _center_window(self, window, width, height):
        """将窗口居中显示"""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")