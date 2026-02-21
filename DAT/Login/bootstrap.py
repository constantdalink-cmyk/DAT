#!/usr/bin/env python3
"""
DAT PE 端启动引导
在 WinPE 环境中启动救援界面
"""

import os
import sys


def find_dat_root():
    """扫描所有磁盘查找 DAT 仓库"""
    for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
        sig_path = f"{letter}:\\.DAT\\dat.sig"
        if os.path.exists(sig_path):
            root = f"{letter}:\\.DAT"
            # 验证完整性
            if os.path.exists(os.path.join(root, 'Runtime', 'python.exe')):
                if os.path.exists(os.path.join(root, 'Logic', 'ui_rescue.py')):
                    return root
    return None


def setup_environment(dat_root):
    """设置环境变量和路径"""
    os.environ['DAT_ROOT'] = dat_root
    
    # 添加 Logic 目录到 Python 路径
    logic_path = os.path.join(dat_root, 'Logic')
    if logic_path not in sys.path:
        sys.path.insert(0, logic_path)


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("        DAT 系统急救 - 启动中...")
    print("=" * 50 + "\n")
    
    # 查找仓库
    dat_root = find_dat_root()
    
    if not dat_root:
        print("\n[错误] 未找到 DAT 仓库！")
        print("\n可能的原因：")
        print("  1. 存放仓库的硬盘未被识别")
        print("  2. 仓库所在分区已加密")
        print("  3. 仓库文件已损坏或被删除")
        print("\n" + "=" * 50)
        input("\n按回车键退出...")
        return 1
    
    print(f"[OK] 找到仓库: {dat_root}")
    
    # 设置环境
    setup_environment(dat_root)
    
    # 启动界面
    try:
        print("[OK] 启动救援界面...")
        from ui_rescue import launch
        launch()
        return 0
    except Exception as e:
        print(f"\n[错误] 启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
        return 1


if __name__ == "__main__":
    sys.exit(main())