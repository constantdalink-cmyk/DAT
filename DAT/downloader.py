"""
DAT 下载管理器
"""

import os
import requests
import threading
import time

from utils import logger, format_size
from config import CHUNK_SIZE, DOWNLOAD_TIMEOUT


class DownloadError(Exception):
    pass


class Downloader:

    def __init__(self, repo):
        self.repo = repo
        self.cancelled = False
        self._speed = 0
        self._last_downloaded = 0
        self._last_time = 0

    @property
    def temp_dir(self):
        path = self.repo.get_path('temp')
        os.makedirs(path, exist_ok=True)
        return path

    @property
    def images_dir(self):
        path = self.repo.get_path('images')
        os.makedirs(path, exist_ok=True)
        return path

    def download(self, url, filename=None, progress_callback=None,
                 complete_callback=None, error_callback=None):
        self.cancelled = False

        def task():
            try:
                path = self._do_download(url, filename, progress_callback)
                if not self.cancelled and complete_callback:
                    complete_callback(path)
            except Exception as ex:
                if not self.cancelled and error_callback:
                    error_callback(str(ex))

        t = threading.Thread(target=task, daemon=True)
        t.start()

    def _do_download(self, url, filename=None, progress_callback=None):
        if not filename:
            filename = self._filename_from_url(url)

        temp_file = os.path.join(self.temp_dir, filename + ".partial")
        final_file = os.path.join(self.images_dir, filename)

        # 已存在
        if os.path.exists(final_file):
            logger.info(f"文件已存在: {filename}")
            return final_file

        # 断点续传
        downloaded = 0
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        }

        if os.path.exists(temp_file):
            downloaded = os.path.getsize(temp_file)
            headers["Range"] = f"bytes={downloaded}-"
            logger.info(f"断点续传: 已下载 {format_size(downloaded)}")

        logger.info(f"下载: {filename}")
        logger.info(f"URL: {url[:100]}...")

        self._last_downloaded = downloaded
        self._last_time = time.time()

        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=DOWNLOAD_TIMEOUT)

            if resp.status_code == 416:
                downloaded = 0
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                headers.pop("Range", None)
                resp = requests.get(url, headers=headers, stream=True, timeout=DOWNLOAD_TIMEOUT)

            resp.raise_for_status()

            total = downloaded
            cl = resp.headers.get("Content-Length")
            if cl:
                total += int(cl)

            mode = "ab" if downloaded > 0 else "wb"

            with open(temp_file, mode) as f:
                for chunk in resp.iter_content(CHUNK_SIZE):
                    if self.cancelled:
                        raise DownloadError("下载已取消")
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        speed, eta = self._calc_speed(downloaded, total)
                        if progress_callback:
                            progress_callback(downloaded, total, speed, eta)

            # 完成
            if os.path.exists(final_file):
                os.remove(final_file)
            os.rename(temp_file, final_file)
            logger.info(f"下载完成: {filename}")
            return final_file

        except requests.exceptions.Timeout:
            raise DownloadError("连接超时")
        except requests.exceptions.ConnectionError:
            raise DownloadError("网络连接失败")
        except requests.exceptions.HTTPError as ex:
            raise DownloadError(f"HTTP 错误: {ex.response.status_code}")

    def _filename_from_url(self, url):
        path = url.split("?")[0]
        name = os.path.basename(path)
        if not name.endswith(".iso"):
            name = "Windows.iso"
        return name

    def _calc_speed(self, downloaded, total):
        now = time.time()
        dt = now - self._last_time
        if dt >= 1.0:
            self._speed = (downloaded - self._last_downloaded) / dt
            self._last_downloaded = downloaded
            self._last_time = now
        eta = 0
        if self._speed > 0 and total > downloaded:
            eta = int((total - downloaded) / self._speed)
        return self._speed, eta

    def cancel(self):
        self.cancelled = True