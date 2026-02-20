"""
DAT 引导注入
负责将 WinPE 启动项注入到 Windows 引导管理器
"""

import subprocess
import re
import os

from utils import logger, run_command
from config import BOOT_ENTRY_NAME


class BootInjector:
    """引导注入器类"""
    
    def __init__(self, repo):
        self.repo = repo
        self.drive = repo.get_drive()
        self.core_dir = repo.get_path('core')
    
    def inject(self):
        """注入启动项"""
        logger.info("开始注入启动项...")
        
        # 验证必要文件
        wim_path = os.path.join(self.core_dir, 'DATBoot.wim')
        sdi_path = os.path.join(self.core_dir, 'boot.sdi')
        
        if not os.path.exists(wim_path):
            raise FileNotFoundError(f"DATBoot.wim 不存在: {wim_path}")
        if not os.path.exists(sdi_path):
            raise FileNotFoundError(f"boot.sdi 不存在: {sdi_path}")
        
        # 检查是否已存在
        if self._find_existing_entry():
            logger.info("启动项已存在，无需重复注入")
            return True
        
        # 注入流程
        try:
            self._create_ramdisk_options()
            guid = self._create_boot_entry()
            self._configure_boot_entry(guid)
            self._add_to_menu(guid)
            
            logger.info("启动项注入成功")
            return True
            
        except Exception as e:
            logger.error(f"注入失败: {e}")
            raise
    
    def _find_existing_entry(self):
        """检查启动项是否已存在"""
        result = run_command(['bcdedit', '/enum', 'osloader'], check=False)
        return BOOT_ENTRY_NAME in result.stdout
    
    def _create_ramdisk_options(self):
        """创建 RAMDisk 选项"""
        logger.debug("创建 RAMDisk 选项...")
        
        sdi_path = f'\\.DAT\\Core\\boot.sdi'
        
        # 尝试创建（可能已存在）
        run_command(['bcdedit', '/create', '{ramdiskoptions}', '/d', 'DAT Ramdisk'], check=False)
        
        run_command([
            'bcdedit', '/set', '{ramdiskoptions}',
            'ramdisksdidevice', f'partition={self.drive}:'
        ])
        
        run_command([
            'bcdedit', '/set', '{ramdiskoptions}',
            'ramdisksdipath', sdi_path
        ])
    
    def _create_boot_entry(self):
        """创建启动项并返回 GUID"""
        logger.debug("创建启动项...")
        
        result = run_command([
            'bcdedit', '/create',
            '/d', BOOT_ENTRY_NAME,
            '/application', 'osloader'
        ])
        
        # 从输出中提取 GUID
        match = re.search(r'\{[a-f0-9-]+\}', result.stdout + result.stderr)
        if not match:
            raise RuntimeError("无法获取启动项 GUID")
        
        guid = match.group(0)
        logger.debug(f"GUID: {guid}")
        return guid
    
    def _configure_boot_entry(self, guid):
        """配置启动项"""
        logger.debug("配置启动项...")
        
        wim_path = f'\\.DAT\\Core\\DATBoot.wim'
        
        # 设置设备
        device_value = f'ramdisk=[{self.drive}:]{wim_path},{{ramdiskoptions}}'
        
        run_command(['bcdedit', '/set', guid, 'device', device_value])
        run_command(['bcdedit', '/set', guid, 'osdevice', device_value])
        run_command(['bcdedit', '/set', guid, 'systemroot', '\\Windows'])
        run_command(['bcdedit', '/set', guid, 'winpe', 'yes'])
        run_command(['bcdedit', '/set', guid, 'detecthal', 'yes'])
    
    def _add_to_menu(self, guid):
        """添加到启动菜单"""
        logger.debug("添加到启动菜单...")
        
        run_command(['bcdedit', '/displayorder', guid, '/addlast'])
        run_command(['bcdedit', '/timeout', '5'])
    
    def remove(self):
        """移除启动项"""
        logger.info("移除启动项...")
        
        # 枚举所有启动项，找到 DAT 的 GUID
        result = run_command(['bcdedit', '/enum', 'osloader'], check=False)
        
        # 解析输出找到 DAT 条目
        current_guid = None
        for line in result.stdout.split('\n'):
            if 'identifier' in line.lower():
                match = re.search(r'\{[a-f0-9-]+\}', line)
                if match:
                    current_guid = match.group(0)
            elif BOOT_ENTRY_NAME in line and current_guid:
                run_command(['bcdedit', '/delete', current_guid], check=False)
                logger.info(f"已删除: {current_guid}")
                current_guid = None