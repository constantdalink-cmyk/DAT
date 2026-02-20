"""
DAT 核心安装器
负责执行系统重装
"""

import os
import sys
import subprocess
import tempfile

# 尝试导入 wmi（PE 环境可能没有）
try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False


class InstallError(Exception):
    """安装错误"""
    pass


class Installer:
    """系统安装器"""
    
    def __init__(self):
        self.dat_root = os.environ.get('DAT_ROOT', '')
    
    def install(self, image_path, progress_callback=None):
        """
        执行系统安装
        
        Args:
            image_path: ISO 镜像路径
            progress_callback: 进度回调 (message, percentage)
        """
        def report(msg, pct):
            print(f"[{pct:3d}%] {msg}")
            if progress_callback:
                progress_callback(msg, pct)
        
        try:
            report("安全检查...", 5)
            self._safety_check()
            
            report("准备目标磁盘...", 10)
            target_disk = self._get_system_disk_number()
            
            report("清理并分区...", 15)
            partitions = self._prepare_disk(target_disk)
            
            report("挂载镜像...", 25)
            iso_drive = self._mount_iso(image_path)
            
            try:
                report("查找安装文件...", 30)
                wim_path = self._find_wim(iso_drive)
                
                report("释放系统文件（需要 10-30 分钟）...", 35)
                self._apply_image(wim_path, partitions['windows'])
                
                report("配置启动项...", 90)
                self._fix_boot(partitions)
                
            finally:
                report("清理临时文件...", 95)
                self._unmount_iso(image_path)
            
            report("安装完成！", 100)
            return True
            
        except Exception as e:
            raise InstallError(f"安装失败: {e}")
    
    def _safety_check(self):
        """安全检查：确保不会清除仓库所在盘"""
        if not self.dat_root:
            raise InstallError("未设置 DAT_ROOT 环境变量")
        
        repo_drive = self.dat_root[0].upper()
        
        # 获取 C 盘所在磁盘
        target_disk = self._get_system_disk_number()
        repo_disk = self._get_disk_number(repo_drive)
        
        if target_disk == repo_disk:
            raise InstallError(
                f"安全检查失败！\n"
                f"目标磁盘（磁盘 {target_disk}）与仓库所在盘相同。\n"
                f"拒绝执行以防止数据丢失。"
            )
    
    def _get_system_disk_number(self):
        """获取系统盘（C:）的磁盘编号"""
        return self._get_disk_number('C')
    
    def _get_disk_number(self, drive_letter):
        """获取指定盘符的磁盘编号"""
        drive = drive_letter.upper()
        
        # 方法1: 使用 WMI
        if HAS_WMI:
            try:
                c = wmi.WMI()
                for logical in c.Win32_LogicalDisk():
                    if logical.DeviceID == f"{drive}:":
                        for part in logical.associators("Win32_LogicalDiskToPartition"):
                            for disk in part.associators("Win32_DiskDriveToDiskPartition"):
                                return int(disk.Index)
            except Exception:
                pass
        
        # 方法2: 使用 diskpart
        script = f"select volume {drive}\ndetail volume\n"
        result = self._run_diskpart(script)
        
        import re
        match = re.search(r'Disk\s+(\d+)', result, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        raise InstallError(f"无法确定 {drive}: 所在磁盘编号")
    
    def _prepare_disk(self, disk_number):
        """准备目标磁盘（清理+分区）"""
        is_uefi = self._is_uefi()
        
        if is_uefi:
            # UEFI + GPT
            script = f"""
select disk {disk_number}
clean
convert gpt
create partition efi size=260
format fs=fat32 quick label=System
assign letter=S
create partition msr size=16
create partition primary
format fs=ntfs quick label=Windows
assign letter=W
exit
"""
        else:
            # Legacy BIOS + MBR
            script = f"""
select disk {disk_number}
clean
convert mbr
create partition primary size=500
format fs=ntfs quick label=System
active
assign letter=S
create partition primary
format fs=ntfs quick label=Windows
assign letter=W
exit
"""
        
        self._run_diskpart(script)
        
        return {
            'system': 'S:',
            'windows': 'W:'
        }
    
    def _is_uefi(self):
        """检查是否为 UEFI 启动"""
        # PE 中检查 firmware 类型
        try:
            result = subprocess.run(
                ['wpeutil', 'UpdateBootInfo'],
                capture_output=True
            )
            
            # 检查注册表
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"System\CurrentControlSet\Control"
            )
            value, _ = winreg.QueryValueEx(key, "PEFirmwareType")
            return value == 2  # 2 = UEFI, 1 = BIOS
        except Exception:
            # 默认假设 UEFI
            return True
    
    def _run_diskpart(self, script):
        """运行 diskpart 脚本"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write(script)
            script_path = f.name
        
        try:
            result = subprocess.run(
                ['diskpart', '/s', script_path],
                capture_output=True,
                text=True
            )
            return result.stdout
        finally:
            os.unlink(script_path)
    
    def _mount_iso(self, iso_path):
        """挂载 ISO 镜像"""
        result = subprocess.run([
            'powershell', '-Command',
            f'(Mount-DiskImage -ImagePath "{iso_path}" -PassThru | Get-Volume).DriveLetter'
        ], capture_output=True, text=True)
        
        drive_letter = result.stdout.strip()
        if not drive_letter:
            raise InstallError("无法挂载 ISO 镜像")
        
        return f"{drive_letter}:"
    
    def _unmount_iso(self, iso_path):
        """卸载 ISO 镜像"""
        subprocess.run([
            'powershell', '-Command',
            f'Dismount-DiskImage -ImagePath "{iso_path}"'
        ], capture_output=True)
    
    def _find_wim(self, iso_drive):
        """查找 install.wim 或 install.esd"""
        for name in ['install.wim', 'install.esd']:
            path = os.path.join(iso_drive, 'sources', name)
            if os.path.exists(path):
                return path
        
        raise InstallError("未在镜像中找到 install.wim 或 install.esd")
    
    def _apply_image(self, wim_path, target_drive):
        """释放系统镜像"""
        result = subprocess.run([
            'dism', '/Apply-Image',
            f'/ImageFile:{wim_path}',
            '/Index:1',
            f'/ApplyDir:{target_drive}\\'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise InstallError(f"DISM 错误: {result.stderr}")
    
    def _fix_boot(self, partitions):
        """修复启动项"""
        result = subprocess.run([
            'bcdboot',
            f'{partitions["windows"]}\\Windows',
            '/s', partitions['system'],
            '/f', 'ALL'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise InstallError(f"BCDBoot 错误: {result.stderr}")