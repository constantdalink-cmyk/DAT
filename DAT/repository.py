"""
DAT 仓库管理
"""

import os
import sys
import zipfile
import shutil

from utils import logger, set_hidden, format_size
from config import REPO_FOLDER, SIGNATURE_FILE, DIRS


class Repository:

    def __init__(self):
        self.root = self._find_root()

    def _find_root(self):
        # 方法1: 从当前脚本位置查找
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # 检查当前目录
        sig = os.path.join(script_dir, SIGNATURE_FILE)
        if os.path.exists(sig):
            return script_dir

        # 检查父目录
        parent = os.path.dirname(script_dir)
        sig = os.path.join(parent, SIGNATURE_FILE)
        if os.path.exists(sig):
            return parent

        # 检查 .DAT 子目录
        dat_dir = os.path.join(script_dir, REPO_FOLDER)
        sig = os.path.join(dat_dir, SIGNATURE_FILE)
        if os.path.exists(sig):
            return dat_dir

        # 方法2: 扫描所有盘
        for letter in 'DEFGHIJKLMNOPQRSTUVWXYZ':
            path = f"{letter}:\\{REPO_FOLDER}"
            if os.path.exists(os.path.join(path, SIGNATURE_FILE)):
                return path

        return None

    def exists(self):
        if self.root is None:
            return False
        return os.path.exists(os.path.join(self.root, SIGNATURE_FILE))

    def initialize(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        drive = os.path.splitdrive(script_dir)[0]
        self.root = os.path.join(drive + os.sep, REPO_FOLDER)

        logger.info(f"初始化仓库: {self.root}")

        # 创建所有目录
        self._ensure_dirs()

        # 签名文件
        sig_path = os.path.join(self.root, SIGNATURE_FILE)
        with open(sig_path, 'w') as f:
            f.write('DAT')

        set_hidden(self.root)

        # 解压 Runtime
        runtime_zip = os.path.join(script_dir, 'Runtime.zip')
        if os.path.exists(runtime_zip):
            logger.info("解压 Runtime.zip...")
            with zipfile.ZipFile(runtime_zip, 'r') as z:
                z.extractall(os.path.join(self.root, DIRS['runtime']))

        # 复制 Logic
        logic_src = os.path.join(script_dir, 'Logic')
        if os.path.exists(logic_src):
            shutil.copytree(logic_src, os.path.join(self.root, DIRS['logic']),
                            dirs_exist_ok=True)

        # 复制 Core
        core_src = os.path.join(script_dir, 'Core')
        if os.path.exists(core_src):
            shutil.copytree(core_src, os.path.join(self.root, DIRS['core']),
                            dirs_exist_ok=True)

    def _ensure_dirs(self):
        """确保所有子目录存在"""
        if not self.root:
            return
        for name, subdir in DIRS.items():
            dir_path = os.path.join(self.root, subdir)
            os.makedirs(dir_path, exist_ok=True)

    def get_path(self, name):
        """获取子目录路径（自动创建）"""
        if name in DIRS:
            path = os.path.join(self.root, DIRS[name])
        else:
            path = os.path.join(self.root, name)
        # 自动创建目录
        os.makedirs(path, exist_ok=True)
        return path

    def get_images(self):
        images_dir = self.get_path('images')
        result = []
        if os.path.exists(images_dir):
            for filename in os.listdir(images_dir):
                if filename.lower().endswith('.iso'):
                    path = os.path.join(images_dir, filename)
                    size = os.path.getsize(path)
                    result.append({
                        'name': os.path.splitext(filename)[0],
                        'filename': filename,
                        'path': path,
                        'size': size,
                        'size_str': format_size(size)
                    })
        return result

    def has_images(self):
        return len(self.get_images()) > 0

    def has_boot_files(self):
        core_dir = self.get_path('core')
        wim = os.path.join(core_dir, 'DATBoot.wim')
        sdi = os.path.join(core_dir, 'boot.sdi')
        return os.path.exists(wim) and os.path.exists(sdi)

    def get_drive(self):
        if self.root:
            return self.root[0].upper()
        return None