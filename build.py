#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨平台打包脚本
支持 Windows、Linux、macOS

使用方法:
    Windows:   python build.py
    Linux:     python3 build.py
    macOS:     python3 build.py
"""

import os
import sys
import shutil
import subprocess
import platform

# 项目配置
APP_NAME = "ClashMerge"
SCRIPT_NAME = "clash_tools.py"
ICON_FILE = ""  # 图标文件路径，留空则使用默认图标

# 打包输出目录
DIST_DIR = "dist"


def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        subprocess.run(['pyinstaller', '--version'], 
                      capture_output=True, check=True)
        print("✓ PyInstaller 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ PyInstaller 未安装，正在安装...")
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], 
                          check=True)
            print("✓ PyInstaller 安装成功")
            return True
        except subprocess.CalledProcessError:
            print("✗ PyInstaller 安装失败，请手动运行: pip install pyinstaller")
            return False


def get_spec_content():
    """生成 PyInstaller spec 文件内容"""
    # 隐藏控制台窗口的配置
    console = platform.system() == "Windows"
    
    spec = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{SCRIPT_NAME}'],
    pathex=[],
    binaries=[],
    datas=[
        ('sources.txt', '.'),
    ],
    hiddenimports=['requests', 'yaml', 'urllib3', 'certifi', 'charset_normalizer', 'idna'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{APP_NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    {'console=True,' if console else 'console=False,'}
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    {'icon=None,' if not ICON_FILE else f"icon='{ICON_FILE}',"}
)
"""
    return spec


def build_spec_file():
    """生成 spec 文件"""
    spec_content = get_spec_content()
    spec_file = f"{APP_NAME}.spec"
    
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"✓ 已生成 {spec_file}")
    return spec_file


def clean_build():
    """清理之前的构建文件"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"清理 {dir_name}/ ...")
            shutil.rmtree(dir_name)
    
    # 删除旧的 exe 文件
    for f in os.listdir('.'):
        if f.endswith('.spec'):
            os.remove(f)
            print(f"删除 {f}")


def run_pyinstaller(spec_file):
    """运行 PyInstaller"""
    print("\n开始打包...")
    
    cmd = ['pyinstaller', spec_file, '--clean']
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n✓ 打包成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        return False


def show_result():
    """显示打包结果"""
    system = platform.system()
    
    if system == "Windows":
        exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
    elif system == "Linux":
        exe_path = os.path.join(DIST_DIR, APP_NAME)
    elif system == "Darwin":
        exe_path = os.path.join(DIST_DIR, APP_NAME)
    else:
        exe_path = os.path.join(DIST_DIR, APP_NAME)
    
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path) / (1024 * 1024)  # MB
        print(f"\n{'='*50}")
        print(f"打包完成!")
        print(f"输出路径: {os.path.abspath(exe_path)}")
        print(f"文件大小: {size:.2f} MB")
        print(f"{'='*50}")
        
        # 复制 sources.txt 到 dist 目录
        if os.path.exists('sources.txt'):
            shutil.copy('sources.txt', DIST_DIR)
            print(f"已复制 sources.txt 到 {DIST_DIR}/")
        
        print("\n使用方法:")
        print(f"  cd {DIST_DIR}")
        if system == "Windows":
            print(f"  .\\{APP_NAME}.exe")
        else:
            print(f"  ./{APP_NAME}")
    else:
        print("✗ 未找到生成的可执行文件")


def build_windows():
    """Windows 平台构建"""
    print("\n" + "="*50)
    print("Windows 平台打包")
    print("="*50)
    
    if not check_pyinstaller():
        return
    
    clean_build()
    spec_file = build_spec_file()
    
    if run_pyinstaller(spec_file):
        show_result()


def build_linux():
    """Linux 平台构建"""
    print("\n" + "="*50)
    print("Linux 平台打包")
    print("="*50)
    
    if not check_pyinstaller():
        return
    
    clean_build()
    spec_file = build_spec_file()
    
    if run_pyinstaller(spec_file):
        show_result()


def build_macos():
    """macOS 平台构建"""
    print("\n" + "="*50)
    print("macOS 平台打包")
    print("="*50)
    
    if not check_pyinstaller():
        return
    
    clean_build()
    spec_file = build_spec_file()
    
    if run_pyinstaller(spec_file):
        show_result()


def main():
    system = platform.system()
    
    print(f"\nClashMerge 跨平台打包工具")
    print(f"检测到系统: {system}")
    print()
    
    if system == "Windows":
        build_windows()
    elif system == "Linux":
        build_linux()
    elif system == "Darwin":
        build_macos()
    else:
        print(f"不支持的系统: {system}")
        sys.exit(1)


if __name__ == '__main__':
    main()
