"""
DAT 工具函数
"""

import os
import sys
import ctypes
import subprocess
import hashlib
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[DAT] %(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('DAT')


def is_admin():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def run_as_admin():
    """以管理员权限重新启动程序"""
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)


def get_system_drive():
    """获取系统盘盘符"""
    return os.environ.get('SystemDrive', 'C:')[0].upper()


def is_on_system_drive(path=None):
    """检查路径是否在系统盘"""
    if path is None:
        path = sys.executable
    current = os.path.splitdrive(path)[0].upper().rstrip(':')
    system = get_system_drive()
    return current == system


def is_uefi():
    """检查是否为 UEFI 启动"""
    # 方法1: 检查 winload.efi
    if os.path.exists(r"C:\Windows\System32\winload.efi"):
        return True
    # 方法2: 检查 EFI 系统分区
    try:
        result = subprocess.run(
            ['bcdedit', '/enum', 'firmware'],
            capture_output=True, text=True
        )
        return 'firmware' in result.stdout.lower()
    except Exception:
        pass
    return False


def calculate_sha256(filepath, progress_callback=None):
    """计算文件 SHA-256"""
    sha256 = hashlib.sha256()
    total_size = os.path.getsize(filepath)
    processed = 0
    
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
            processed += len(chunk)
            if progress_callback:
                progress_callback(processed, total_size)
    
    return sha256.hexdigest().upper()


def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def set_hidden(path):
    """设置文件/文件夹为隐藏"""
    try:
        ctypes.windll.kernel32.SetFileAttributesW(path, 0x02)
    except Exception as e:
        logger.warning(f"设置隐藏属性失败: {e}")


def run_command(cmd, check=True, capture=True):
    """执行命令"""
    logger.debug(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check
    )
    return result


def show_error_dialog(title, message):
    """显示错误对话框"""
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message)
    root.destroy()


def show_info_dialog(title, message):
    """显示信息对话框"""
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()