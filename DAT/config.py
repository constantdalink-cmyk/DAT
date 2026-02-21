"""
DAT 配置文件
"""

VERSION = "1.0.0"
APP_NAME = "DAT 系统急救"

REPO_FOLDER = ".DAT"
SIGNATURE_FILE = "dat.sig"
MIN_FREE_SPACE_GB = 20

DIRS = {
    'runtime': 'Runtime',
    'logic': 'Logic',
    'core': 'Core',
    'images': 'Images',
    'temp': 'Temp'
}

CHUNK_SIZE = 1024 * 1024  # 1MB
DOWNLOAD_TIMEOUT = 60

BOOT_ENTRY_NAME = "DAT 系统急救"