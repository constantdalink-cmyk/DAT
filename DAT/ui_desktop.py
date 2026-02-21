"""
DAT 桌面端界面
"""

import os
import webbrowser
import threading
from tkinter import filedialog
import customtkinter as ctk

from utils import logger, format_size
from microsoft_iso import MicrosoftISO
from boot_inject import BootInjector
from config import APP_NAME, VERSION


class DesktopUI:

    def __init__(self, repo, locked=False):
        self.repo = repo
        self.locked = locked
        self.download_running = False
        self._ms = MicrosoftISO()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    def run(self):
        self.root = ctk.CTk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("720x700")
        self.root.resizable(False, False)
        self._center(720, 700)

        if not self.repo.has_images():
            self._page_download()
        else:
            self._page_main()

        self.root.mainloop()

    def _center(self, w, h):
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    # ============================================================
    #                       下载页面
    # ============================================================

    def _page_download(self):
        self._clear()

        ctk.CTkLabel(
            self.root, text="🚀 DAT 系统镜像获取",
            font=("Microsoft YaHei", 26, "bold")
        ).pack(pady=(20, 5))

        ctk.CTkLabel(
            self.root,
            text="第一步：下载 Windows ISO  →  第二步：添加到 DAT",
            font=("Microsoft YaHei", 13), text_color="gray"
        ).pack(pady=(0, 15))

        # ========== 第一步：选择版本下载 ==========
        step1 = ctk.CTkFrame(self.root)
        step1.pack(fill="x", padx=40, pady=5)

        ctk.CTkLabel(
            step1, text="① 选择版本，点击下载",
            font=("Microsoft YaHei", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # 版本列表（可滚动）
        versions_frame = ctk.CTkScrollableFrame(step1, height=250)
        versions_frame.pack(fill="x", padx=15, pady=(0, 15))

        for ver in self._ms.get_versions():
            self._create_version_card(versions_frame, ver)

        # ========== 第二步：添加 ISO ==========
        step2 = ctk.CTkFrame(self.root)
        step2.pack(fill="x", padx=40, pady=10)

        ctk.CTkLabel(
            step2, text="② 下载完成后，添加 ISO 文件",
            font=("Microsoft YaHei", 15, "bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        btn_frame = ctk.CTkFrame(step2, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="📁 选择已下载的 ISO 文件",
            font=("Microsoft YaHei", 15),
            width=350, height=50,
            command=self._select_local_iso
        ).pack(pady=5)

        ctk.CTkLabel(
            btn_frame,
            text="支持 .iso 格式，文件大小需大于 1GB",
            font=("Microsoft YaHei", 10), text_color="gray"
        ).pack()

        # ========== 状态区域 ==========
        ctk.CTkLabel(
            self.root, text="─" * 60, text_color="#333"
        ).pack(pady=8)

        self.status_label = ctk.CTkLabel(
            self.root, text="",
            font=("Microsoft YaHei", 13)
        )
        self.status_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.root, width=520, height=18)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)

        self.progress_text = ctk.CTkLabel(
            self.root, text="",
            font=("Microsoft YaHei", 11), text_color="gray"
        )
        self.progress_text.pack(pady=3)

    def _create_version_card(self, parent, ver):
        """创建版本卡片"""
        card = ctk.CTkFrame(parent)
        card.pack(fill="x", pady=4, padx=3)

        # 左侧信息
        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=15, pady=10)

        ctk.CTkLabel(
            info, text=f"💿 {ver['name']}",
            font=("Microsoft YaHei", 14, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            info, text=f"大小: {ver['size']}  |  官方原版镜像",
            font=("Microsoft YaHei", 10), text_color="gray"
        ).pack(anchor="w")

        # 右侧按钮
        btn_area = ctk.CTkFrame(card, fg_color="transparent")
        btn_area.pack(side="right", padx=10, pady=10)

        sources = ver.get("sources", [])

        for i, source in enumerate(sources):
            color = "#0078D4" if i == 0 else "#555"
            ctk.CTkButton(
                btn_area,
                text=f"🌐 {source['name']}",
                width=130, height=30,
                font=("Microsoft YaHei", 11),
                fg_color=color,
                command=lambda vid=ver["id"], idx=i, sname=source["name"]:
                    self._open_source(vid, idx, sname)
            ).pack(pady=2)

    def _open_source(self, version_id, source_index, source_name):
        """打开下载源"""
        self._ms.open_download_page(version_id, source_index)
        self.status_label.configure(
            text=f"✅ 已打开 {source_name}，下载完成后点击上方「选择已下载的 ISO 文件」",
            text_color="yellow"
        )

    def _select_local_iso(self):
        """选择本地 ISO"""
        filepath = filedialog.askopenfilename(
            title="选择 Windows ISO 镜像",
            filetypes=[("ISO 镜像", "*.iso"), ("所有文件", "*.*")]
        )
        if not filepath:
            return
        if not filepath.lower().endswith(".iso"):
            self.status_label.configure(text="❌ 请选择 .iso 文件", text_color="red")
            return

        size = os.path.getsize(filepath)
        if size < 1 * 1024**3:
            self.status_label.configure(text="❌ 文件太小，不像系统镜像", text_color="red")
            return

        filename = os.path.basename(filepath)
        self.status_label.configure(
            text=f"正在添加: {filename}",
            text_color="white"
        )
        self.download_running = True

        def do_copy():
            try:
                target_dir = self.repo.get_path("images")
                target = os.path.join(target_dir, filename)

                # 同一文件
                if os.path.abspath(filepath) == os.path.abspath(target):
                    self.root.after(0, lambda t=target: self._add_done(t))
                    return

                # 如果在同一个盘，直接移动（快）
                src_drive = os.path.splitdrive(filepath)[0].upper()
                dst_drive = os.path.splitdrive(target)[0].upper()

                if src_drive == dst_drive:
                    # 同盘复制也用流式，因为可能在用
                    pass

                total = os.path.getsize(filepath)
                copied = 0
                with open(filepath, "rb") as src, open(target, "wb") as dst:
                    while True:
                        chunk = src.read(4 * 1024 * 1024)  # 4MB 块
                        if not chunk:
                            break
                        dst.write(chunk)
                        copied += len(chunk)
                        pct = copied / total
                        self.root.after(0, lambda p=pct, c=copied, t=total:
                            self._update_copy(p, c, t))

                self.root.after(0, lambda t=target: self._add_done(t))

            except Exception as ex:
                msg = str(ex)
                self.root.after(0, lambda m=msg: self._add_fail(m))

        threading.Thread(target=do_copy, daemon=True).start()

    def _update_copy(self, pct, copied, total):
        self.progress_bar.set(pct)
        self.progress_text.configure(
            text=f"{format_size(copied)} / {format_size(total)} ({pct*100:.1f}%)"
        )

    def _add_done(self, filepath):
        self.download_running = False
        self.progress_bar.set(1)
        self.progress_text.configure(text="")

        self.status_label.configure(text="✅ 镜像已添加！", text_color="green")

        # 注入引导项
        try:
            if self.repo.has_boot_files():
                self.status_label.configure(text="正在配置启动项...")
                self.root.update()
                injector = BootInjector(self.repo)
                injector.inject()
        except Exception as ex:
            logger.warning(f"引导注入跳过: {ex}")

        self.status_label.configure(text="✅ 一切就绪！", text_color="green")
        self.root.after(2000, self._page_main)

    def _add_fail(self, error):
        self.download_running = False
        self.status_label.configure(text=f"❌ {error}", text_color="red")

    # ============================================================
    #                       主界面
    # ============================================================

    def _page_main(self):
        self._clear()

        icon = "✅" if not self.locked else "⚠️"
        text = "已就绪" if not self.locked else "受限模式"

        ctk.CTkLabel(
            self.root, text=f"{icon} DAT {text}",
            font=("Microsoft YaHei", 28, "bold")
        ).pack(pady=(50, 30))

        # 镜像列表
        frame = ctk.CTkFrame(self.root)
        frame.pack(pady=15, padx=60, fill="x")

        ctk.CTkLabel(
            frame, text="📦 已添加的系统镜像：",
            font=("Microsoft YaHei", 16, "bold")
        ).pack(anchor="w", padx=25, pady=(20, 12))

        images = self.repo.get_images()
        if images:
            for img in images:
                r = ctk.CTkFrame(frame, fg_color="transparent")
                r.pack(anchor="w", padx=30, pady=5, fill="x")
                ctk.CTkLabel(r, text=f"✓ {img['name']}",
                             font=("Microsoft YaHei", 14)).pack(side="left")
                ctk.CTkLabel(r, text=f"({img['size_str']})",
                             font=("Microsoft YaHei", 12),
                             text_color="gray").pack(side="left", padx=10)
        else:
            ctk.CTkLabel(
                frame, text="  暂无镜像",
                font=("Microsoft YaHei", 13), text_color="gray"
            ).pack(anchor="w", padx=30, pady=10)

        ctk.CTkLabel(frame, text="").pack(pady=8)

        # 使用说明
        if self.locked:
            msg = "⚠️ 程序在系统盘，重装功能已锁定"
            color = "orange"
        else:
            msg = "💡 系统崩溃时 → 重启电脑 → 选择「DAT 系统急救」"
            color = "gray"

        ctk.CTkLabel(
            self.root, text=msg,
            font=("Microsoft YaHei", 14), text_color=color
        ).pack(pady=35)

        # 按钮
        btn = ctk.CTkFrame(self.root, fg_color="transparent")
        btn.pack(pady=25)

        ctk.CTkButton(
            btn, text="📥 添加更多镜像", width=160, height=50,
            font=("Microsoft YaHei", 14),
            command=self._page_download
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn, text="📂 打开目录", width=130, height=50,
            font=("Microsoft YaHei", 14), fg_color="gray",
            command=self._open_images_folder
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn, text="退出", width=90, height=50,
            font=("Microsoft YaHei", 14), fg_color="darkgray",
            command=self.root.destroy
        ).pack(side="left", padx=10)

        # 版本
        ctk.CTkLabel(
            self.root,
            text=f"v{VERSION}  |  仓库: {self.repo.root}",
            font=("Microsoft YaHei", 10), text_color="gray"
        ).pack(side="bottom", pady=20)

    def _open_images_folder(self):
        import subprocess
        path = self.repo.get_path("images")
        os.makedirs(path, exist_ok=True)
        subprocess.Popen(["explorer", path])