"""
Windows ISO 下载
由于微软 API 在部分地区不可用，使用多种备用源
"""

import os
import re
import webbrowser

from utils import logger


class MicrosoftISO:

    VERSIONS = [
        {
            "id": "win11_24h2",
            "name": "Windows 11 24H2 (64位)",
            "size": "约 6.2 GB",
            "sources": [
                {
                    "name": "MSDN I Tell You",
                    "type": "browser",
                    "url": "https://next.itellyou.cn/Original/#cbp=Product?ID=f905b2d9-11e7-4ee3-8b52-407a8571f4e1",
                },
                {
                    "name": "微软官方",
                    "type": "browser",
                    "url": "https://www.microsoft.com/zh-cn/software-download/windows11",
                },
                {
                    "name": "TechBench",
                    "type": "browser",
                    "url": "https://tb.rg-adguard.net/public.php",
                },
            ],
        },
        {
            "id": "win11_23h2",
            "name": "Windows 11 23H2 (64位)",
            "size": "约 6.2 GB",
            "sources": [
                {
                    "name": "MSDN I Tell You",
                    "type": "browser",
                    "url": "https://next.itellyou.cn/Original/#cbp=Product?ID=42e2ac3c-14cf-44f1-8a7c-71e8bac8e417",
                },
                {
                    "name": "微软官方",
                    "type": "browser",
                    "url": "https://www.microsoft.com/zh-cn/software-download/windows11",
                },
            ],
        },
        {
            "id": "win10_22h2",
            "name": "Windows 10 22H2 (64位)",
            "size": "约 5.8 GB",
            "sources": [
                {
                    "name": "MSDN I Tell You",
                    "type": "browser",
                    "url": "https://next.itellyou.cn/Original/#cbp=Product?ID=f905b2d9-11e7-4ee3-8b52-407a8571f4e1",
                },
                {
                    "name": "微软官方",
                    "type": "browser",
                    "url": "https://www.microsoft.com/zh-cn/software-download/windows10",
                },
            ],
        },
    ]

    def get_versions(self):
        return self.VERSIONS

    def open_download_page(self, version_id, source_index=0):
        """打开下载页面"""
        for v in self.VERSIONS:
            if v["id"] == version_id:
                sources = v["sources"]
                if source_index < len(sources):
                    url = sources[source_index]["url"]
                    webbrowser.open(url)
                    return sources[source_index]["name"]
        return None