"""
DAT PE 端救援界面
在 WinPE 环境中显示的图形界面
"""

import os
import subprocess
import customtkinter as ctk

from installer import Installer, InstallError


class RescueUI:
    """救援界面类"""
    
    def __init__(self):
        self.dat_root = os.environ.get('DAT_ROOT', '')
        self.installer = Installer()
    
    def run(self):
        """运行界面"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("DAT 系统急救")
        
        # 全屏
        self.root.attributes('-fullscreen', True)
        
        # 允许 ESC 退出全屏
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        
        self._build_ui()
        self.root.mainloop()
    
    def _build_ui(self):
        """构建界面"""
        # 主容器
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=50, pady=30)
        
        # 标题
        ctk.CTkLabel(
            main_frame,
            text="🚀 DAT 系统急救",
            font=("Microsoft YaHei", 48, "bold")
        ).pack(pady=(30, 20))
        
        ctk.CTkLabel(
            main_frame,
            text="从本地镜像恢复您的 Windows 系统",
            font=("Microsoft YaHei", 18),
            text_color="gray"
        ).pack(pady=(0, 40))
        
        # 镜像选择框
        select_frame = ctk.CTkFrame(main_frame)
        select_frame.pack(pady=20, padx=100, fill="x")
        
        ctk.CTkLabel(
            select_frame,
            text="📦 选择系统镜像：",
            font=("Microsoft YaHei", 20, "bold")
        ).pack(anchor="w", padx=30, pady=(25, 15))
        
        # 获取镜像列表
        images = self._get_images()
        
        if images:
            self.selected_image = ctk.StringVar(value=images[0]['path'])
            
            for img in images:
                ctk.CTkRadioButton(
                    select_frame,
                    text=f"{img['name']}  ({img['size_str']})",
                    variable=self.selected_image,
                    value=img['path'],
                    font=("Microsoft YaHei", 18)
                ).pack(anchor="w", padx=50, pady=12)
        else:
            ctk.CTkLabel(
                select_frame,
                text="⚠️ 未找到可用的系统镜像！",
                font=("Microsoft YaHei", 18),
                text_color="orange"
            ).pack(pady=30)
            self.selected_image = None
        
        ctk.CTkLabel(select_frame, text="").pack(pady=10)
        
        # 状态显示
        self.status_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=("Microsoft YaHei", 16)
        )
        self.status_label.pack(pady=15)
        
        # 进度条
        self.progress_bar = ctk.CTkProgressBar(main_frame, width=600, height=25)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        # 进度文字
        self.progress_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=("Microsoft YaHei", 14),
            text_color="gray"
        )
        self.progress_label.pack(pady=5)
        
        # 按钮区域
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=40)
        
        self.install_btn = ctk.CTkButton(
            btn_frame,
            text="💿 开始重装系统",
            font=("Microsoft YaHei", 22, "bold"),
            width=320,
            height=80,
            command=self._on_install,
            state="normal" if images else "disabled"
        )
        self.install_btn.pack(side="left", padx=25)
        
        ctk.CTkButton(
            btn_frame,
            text="🔧 命令行",
            font=("Microsoft YaHei", 16),
            width=150,
            height=80,
            fg_color="gray",
            command=self._open_cmd
        ).pack(side="left", padx=25)
        
        ctk.CTkButton(
            btn_frame,
            text="🔄 重启",
            font=("Microsoft YaHei", 16),
            width=150,
            height=80,
            fg_color="darkgray",
            command=self._reboot
        ).pack(side="left", padx=25)
        
        # 警告
        ctk.CTkLabel(
            main_frame,
            text="⚠️ 警告：重装将清空 C 盘所有数据！请确保重要文件已备份。",
            font=("Microsoft YaHei", 16),
            text_color="red"
        ).pack(pady=30)
    
    def _get_images(self):
        """获取可用的镜像列表"""
        images_dir = os.path.join(self.dat_root, 'Images')
        result = []
        
        if os.path.exists(images_dir):
            for filename in os.listdir(images_dir):
                if filename.lower().endswith('.iso'):
                    path = os.path.join(images_dir, filename)
                    size = os.path.getsize(path)
                    result.append({
                        'name': os.path.splitext(filename)[0],
                        'path': path,
                        'size': size,
                        'size_str': f"{size / 1024**3:.1f} GB"
                    })
        
        return result
    
    def _on_install(self):
        """开始安装"""
        if not self.selected_image:
            return
        
        # 最终确认
        if not self._confirm_install():
            return
        
        self.install_btn.configure(state="disabled")
        self.status_label.configure(text="准备中...", text_color="white")
        
        # 在线程中执行安装
        import threading
        
        def install_task():
            try:
                image_path = self.selected_image.get()
                
                def on_progress(msg, pct):
                    self.root.after(0, lambda: self._update_progress(msg, pct))
                
                self.installer.install(image_path, on_progress)
                self.root.after(0, self._on_install_complete)
                
            except Exception as e:
                self.root.after(0, lambda: self._on_install_error(str(e)))
        
        threading.Thread(target=install_task, daemon=True).start()
    
    def _confirm_install(self):
        """确认安装对话框"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("确认")
        dialog.geometry("450x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 450) // 2
        y = (dialog.winfo_screenheight() - 250) // 2
        dialog.geometry(f"+{x}+{y}")
        
        result = {"confirmed": False}
        
        ctk.CTkLabel(
            dialog,
            text="⚠️ 最终确认",
            font=("Microsoft YaHei", 20, "bold"),
            text_color="orange"
        ).pack(pady=(30, 15))
        
        ctk.CTkLabel(
            dialog,
            text="此操作将清空 C 盘所有数据！\n包括桌面文件、下载内容、已安装程序等。\n\n确定要继续吗？",
            font=("Microsoft YaHei", 14),
            justify="center"
        ).pack(pady=15)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        def on_yes():
            result["confirmed"] = True
            dialog.destroy()
        
        def on_no():
            dialog.destroy()
        
        ctk.CTkButton(
            btn_frame, text="取消", width=120, command=on_no
        ).pack(side="left", padx=15)
        
        ctk.CTkButton(
            btn_frame, text="确定重装", width=120,
            fg_color="darkred", command=on_yes
        ).pack(side="left", padx=15)
        
        dialog.wait_window()
        return result["confirmed"]
    
    def _update_progress(self, message, percentage):
        """更新进度"""
        self.status_label.configure(text=message)
        self.progress_bar.set(percentage / 100)
        self.progress_label.configure(text=f"{percentage}%")
    
    def _on_install_complete(self):
        """安装完成"""
        self.status_label.configure(text="✅ 系统安装完成！", text_color="green")
        self.progress_bar.set(1)
        self.progress_label.configure(text="请重启电脑")
        
        self.install_btn.configure(
            text="🔄 重启电脑",
            command=self._reboot,
            state="normal"
        )
    
    def _on_install_error(self, error):
        """安装错误"""
        self.status_label.configure(text=f"❌ {error}", text_color="red")
        self.install_btn.configure(state="normal")
    
    def _open_cmd(self):
        """打开命令行"""
        subprocess.Popen(['cmd.exe'], creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    def _reboot(self):
        """重启电脑"""
        subprocess.run(['wpeutil', 'reboot'])


def launch():
    """启动入口"""
    ui = RescueUI()
    ui.run()


if __name__ == "__main__":
    launch()