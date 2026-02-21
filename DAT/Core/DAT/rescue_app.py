"""
DAT 救援程序 (PE 端)
合并 bootstrap + installer + ui_rescue 为单文件
编译命令: pyinstaller --onefile --noconsole --collect-all customtkinter rescue_app.py
输出 rescue.exe 放入 Core/ 目录
"""

import os
import sys
import subprocess
import tempfile
import ctypes
import threading


# =================================================================
#  常量
# =================================================================

SIGNATURE_FILE = "dat.sig"
REPO_FOLDER = ".DAT"


# =================================================================
#  工具函数
# =================================================================

def format_size(n):
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} PB"


def find_dat_root():
    """扫描所有盘符查找 DAT 仓库"""
    for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        path = f"{letter}:\\{REPO_FOLDER}"
        if os.path.exists(os.path.join(path, SIGNATURE_FILE)):
            return path
    return None


def get_images(dat_root):
    """获取本地镜像列表"""
    images_dir = os.path.join(dat_root, "Images")
    result = []
    if not os.path.isdir(images_dir):
        return result
    for f in sorted(os.listdir(images_dir)):
        if f.lower().endswith(".iso"):
            path = os.path.join(images_dir, f)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            result.append({
                "name": os.path.splitext(f)[0],
                "path": path,
                "size": size,
                "size_str": format_size(size),
            })
    return result


# =================================================================
#  安装器
# =================================================================

class Installer:

    def __init__(self, dat_root):
        self.dat_root = dat_root

    # --------------------------------------------------------------
    #  主流程
    # --------------------------------------------------------------

    def install(self, image_path, progress_cb=None):

        if progress_cb:
            progress_cb("安全检查...", 5)

        target_disk = self._get_disk_number("C")
        repo_disk = self._get_disk_number(self.dat_root[0])

        if target_disk is None:
            raise Exception("无法确定系统盘磁盘号")
        if repo_disk is None:
            raise Exception("无法确定仓库磁盘号")
        if target_disk == repo_disk:
            raise Exception(
                "系统盘与仓库在���一块硬盘，拒绝执行！\n"
                "（清洗此硬盘会导致仓库被一起删除）"
            )

        if progress_cb:
            progress_cb("清理目标磁盘...", 10)
        partitions = self._prepare_disk(target_disk)

        if progress_cb:
            progress_cb("挂载 ISO 镜像...", 20)
        iso_drive = self._mount_iso(image_path)

        try:
            wim_path = self._find_wim(iso_drive)

            if progress_cb:
                progress_cb("释放系统文件（约 10-30 分钟）...", 30)
            self._apply_image(wim_path, partitions["windows"])

            if progress_cb:
                progress_cb("修复启动引导...", 90)
            self._fix_boot(partitions)

        finally:
            self._unmount_iso(image_path)

        if progress_cb:
            progress_cb("✅ 安装完成！", 100)
        return True

    # --------------------------------------------------------------
    #  磁盘号
    # --------------------------------------------------------------

    def _get_disk_number(self, drive_letter):
        """通过 PowerShell 获取盘符对应的物理磁盘号"""
        ps = f'(Get-Partition -DriveLetter "{drive_letter}").DiskNumber'
        try:
            r = subprocess.run(
                ["powershell", "-Command", ps],
                capture_output=True, text=True, timeout=15
            )
            return int(r.stdout.strip())
        except Exception:
            return None

    # --------------------------------------------------------------
    #  分区
    # --------------------------------------------------------------

    def _prepare_disk(self, disk_number):
        uefi = self._detect_uefi()

        if uefi:
            script = (
                f"select disk {disk_number}\n"
                f"clean\n"
                f"convert gpt\n"
                f"create partition efi size=260\n"
                f"format fs=fat32 quick label=System\n"
                f"assign letter=S\n"
                f"create partition msr size=16\n"
                f"create partition primary\n"
                f"format fs=ntfs quick label=Windows\n"
                f"assign letter=W\n"
            )
        else:
            script = (
                f"select disk {disk_number}\n"
                f"clean\n"
                f"convert mbr\n"
                f"create partition primary size=500\n"
                f"format fs=ntfs quick label=System\n"
                f"active\n"
                f"assign letter=S\n"
                f"create partition primary\n"
                f"format fs=ntfs quick label=Windows\n"
                f"assign letter=W\n"
            )

        self._run_diskpart(script)
        return {"system": "S:", "windows": "W:"}

    def _detect_uefi(self):
        """检测固件类型"""
        # 方法 1: GetFirmwareType（Win8+ / PE5+）
        try:
            kernel32 = ctypes.windll.kernel32
            fw_type = ctypes.c_uint(0)
            if kernel32.GetFirmwareType(ctypes.byref(fw_type)):
                return fw_type.value == 2   # 1=BIOS, 2=UEFI
        except Exception:
            pass

        # 方法 2: PE 标志文件
        for p in [r"X:\Windows\System32\winload.efi",
                   r"X:\EFI"]:
            if os.path.exists(p):
                return True

        # 默认 UEFI（2020 年后的电脑几乎全是）
        return True

    def _run_diskpart(self, script):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        tmp.write(script)
        tmp.close()
        try:
            subprocess.run(
                ["diskpart", "/s", tmp.name],
                check=True, timeout=120
            )
        finally:
            os.unlink(tmp.name)

    # --------------------------------------------------------------
    #  ISO 挂载
    # --------------------------------------------------------------

    def _mount_iso(self, iso_path):
        r = subprocess.run(
            ["powershell", "-Command",
             f'(Mount-DiskImage -ImagePath "{iso_path}" -PassThru '
             f'| Get-Volume).DriveLetter'],
            capture_output=True, text=True, timeout=30
        )
        letter = r.stdout.strip()
        if not letter:
            raise Exception("ISO 挂载失败，请检查镜像是否完整")
        return letter + ":"

    def _unmount_iso(self, iso_path):
        subprocess.run(
            ["powershell", "-Command",
             f'Dismount-DiskImage -ImagePath "{iso_path}"'],
            capture_output=True, timeout=30
        )

    # --------------------------------------------------------------
    #  释放 & 引导
    # --------------------------------------------------------------

    def _find_wim(self, iso_drive):
        for name in ["install.wim", "install.esd"]:
            path = os.path.join(iso_drive, "sources", name)
            if os.path.exists(path):
                return path
        raise Exception(
            f"镜像中未找到 install.wim 或 install.esd\n"
            f"（已搜索 {iso_drive}\\sources\\）"
        )

    def _apply_image(self, wim_path, target):
        subprocess.run([
            "dism", "/Apply-Image",
            f"/ImageFile:{wim_path}",
            "/Index:1",
            f"/ApplyDir:{target}\\"
        ], check=True, timeout=3600)

    def _fix_boot(self, partitions):
        subprocess.run([
            "bcdboot",
            f'{partitions["windows"]}\\Windows',
            "/s", partitions["system"],
            "/f", "ALL"
        ], check=True, timeout=60)


# =================================================================
#  救援界面 (GUI)
# =================================================================

class RescueUI:

    def __init__(self, dat_root):
        self.dat_root = dat_root
        self.installing = False

    def run(self):
        import customtkinter as ctk

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("DAT 系统急救")
        self.root.attributes("-fullscreen", True)

        self._build(ctk)
        self.root.mainloop()

    def _build(self, ctk):

        # ── 标题 ──
        ctk.CTkLabel(
            self.root,
            text="🚀 DAT 系统急救",
            font=("Microsoft YaHei", 42, "bold")
        ).pack(pady=(60, 10))

        ctk.CTkLabel(
            self.root,
            text=f"仓库：{self.dat_root}",
            font=("Microsoft YaHei", 13), text_color="gray"
        ).pack(pady=(0, 30))

        # ── 镜像列表 ──
        frame = ctk.CTkFrame(self.root)
        frame.pack(pady=20, padx=120, fill="x")

        ctk.CTkLabel(
            frame, text="📦 本地镜像",
            font=("Microsoft YaHei", 20, "bold")
        ).pack(anchor="w", padx=25, pady=(20, 15))

        images = get_images(self.dat_root)

        if images:
            self.selected_var = ctk.StringVar(value=images[0]["path"])
            for img in images:
                ctk.CTkRadioButton(
                    frame,
                    text=f"{img['name']}    ({img['size_str']})",
                    variable=self.selected_var,
                    value=img["path"],
                    font=("Microsoft YaHei", 17)
                ).pack(anchor="w", padx=40, pady=10)
        else:
            ctk.CTkLabel(
                frame,
                text="⚠️ 未找到系统镜像",
                text_color="orange",
                font=("Microsoft YaHei", 18)
            ).pack(pady=25)

        ctk.CTkLabel(frame, text="").pack(pady=5)

        # ── 进度 ──
        self.status_label = ctk.CTkLabel(
            self.root, text="",
            font=("Microsoft YaHei", 16)
        )
        self.status_label.pack(pady=15)

        self.progress = ctk.CTkProgressBar(
            self.root, width=550, height=22)
        self.progress.pack(pady=8)
        self.progress.set(0)

        # ── 按钮 ──
        btn_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        btn_frame.pack(pady=40)

        if images:
            self.install_btn = ctk.CTkButton(
                btn_frame,
                text="💿 开始重装系统",
                font=("Microsoft YaHei", 22, "bold"),
                width=300, height=75,
                command=self._on_install
            )
            self.install_btn.pack(side="left", padx=25)

        ctk.CTkButton(
            btn_frame,
            text="退出",
            font=("Microsoft YaHei", 18),
            width=160, height=75,
            fg_color="gray",
            command=self.root.destroy
        ).pack(side="left", padx=25)

        # ── 警告 ──
        ctk.CTkLabel(
            self.root,
            text="⚠️ 重装将清空系统盘 (C:) 所有数据！其他盘不受影响。",
            text_color="#FF6666",
            font=("Microsoft YaHei", 17)
        ).pack(pady=35)

    # ----------------------------------------------------------

    def _on_install(self):
        if self.installing:
            return

        import customtkinter as ctk
        dialog = ctk.CTkInputDialog(
            text='输入 "YES" 确认重装\n（将清空 C 盘所有数据）',
            title="最终确认"
        )
        if dialog.get_input() != "YES":
            self.status_label.configure(
                text="已取消", text_color="gray")
            return

        self.installing = True
        self.install_btn.configure(state="disabled", text="安装中...")

        threading.Thread(
            target=self._do_install, daemon=True).start()

    def _do_install(self):
        def cb(msg, pct):
            self.root.after(0, self._update, msg, pct)
        try:
            Installer(self.dat_root).install(
                self.selected_var.get(), cb)
            self.root.after(0, self._done)
        except Exception as e:
            self.root.after(0, self._fail, str(e))

    def _update(self, msg, pct):
        self.status_label.configure(text=msg, text_color="white")
        self.progress.set(pct / 100)

    def _done(self):
        self.status_label.configure(
            text="✅ 安装完成！请重启电脑。",
            text_color="green")
        self.progress.set(1)
        self.install_btn.configure(text="✅ 完成")

    def _fail(self, err):
        self.status_label.configure(
            text=f"❌ 安装失败: {err}", text_color="red")
        self.installing = False
        self.install_btn.configure(
            state="normal", text="💿 重试")


# =================================================================
#  命令行回退（GUI 挂了用这个）
# =================================================================

def cmd_fallback(dat_root, images):
    print("\n" + "=" * 50)
    print("  DAT 命令行安装模式")
    print("=" * 50 + "\n")

    for i, img in enumerate(images, 1):
        print(f"  [{i}] {img['name']}  ({img['size_str']})")
    print(f"  [0] 退出\n")

    try:
        idx = int(input("选择编号: ").strip())
    except ValueError:
        print("无效输入")
        return 1

    if idx == 0:
        return 0
    if idx < 1 or idx > len(images):
        print("编号超出范围")
        return 1

    selected = images[idx - 1]
    print(f"\n即将使用: {selected['name']}")

    if input('输入 YES 确认（将清空 C 盘）: ').strip() != "YES":
        print("已取消")
        return 0

    def cb(msg, pct):
        print(f"  [{pct:3d}%] {msg}")

    try:
        Installer(dat_root).install(selected["path"], cb)
        print("\n✅ 安装完成！")
    except Exception as e:
        print(f"\n❌ 失败: {e}")
        return 1

    input("\n按回车重启...")
    subprocess.run(["wpeutil", "reboot"])
    return 0


# =================================================================
#  入口
# =================================================================

def main():
    print()
    print("=" * 50)
    print("  DAT 系统急救 — 救援模式")
    print("=" * 50)
    print()

    dat_root = find_dat_root()
    if not dat_root:
        print("[错误] 未找到 DAT 仓库")
        print("  请确认仓库所在硬盘已连接且未加密")
        input("\n按回车退出...")
        return 1

    print(f"[OK] 仓库: {dat_root}")

    images = get_images(dat_root)
    if not images:
        print("[错误] 仓库中没有系统镜像")
        input("\n按回车退出...")
        return 1

    print(f"[OK] 找到 {len(images)} 个镜像\n")

    # 尝试 GUI，失败则回退命令行
    try:
        RescueUI(dat_root).run()
    except Exception as e:
        print(f"[警告] GUI 启动失败: {e}")
        print("[回退] 进入命令行模式...\n")
        return cmd_fallback(dat_root, images)

    return 0


if __name__ == "__main__":
    sys.exit(main())
