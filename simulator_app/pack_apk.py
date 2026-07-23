# -*- coding: utf-8 -*-
"""
打包辅助脚本 - 在 Linux/macOS 上运行 buildozer 打包 APK

使用方法:
    python pack_apk.py           # 默认 debug 包
    python pack_apk.py release   # release 签名包

前置条件 (Ubuntu/Debian):
    sudo apt update
    sudo apt install -y python3-pip python3-setuptools
    sudo apt install -y git zip unzip openjdk-17-jdk
    sudo apt install -y autoconf libtool pkg-config
    pip3 install --user buildozer
    export PATH=\$PATH:~/.local/bin

前置条件 (macOS):
    brew install python3 openjdk@17 git
    pip3 install buildozer

然后在该目录下运行:
    buildozer android debug      # 出 debug APK
    buildozer android release    # 出 release APK (需签名)
"""
import subprocess
import sys
import os

MODE = sys.argv[1] if len(sys.argv) > 1 else "debug"

print(f"=== 开始打包 APK ({MODE}) ===")
print(f"工作目录: {os.getcwd()}")
print()

# 检查 buildozer 是否安装
try:
    subprocess.run(["buildozer", "--version"], check=True, capture_output=True)
except (subprocess.CalledProcessError, FileNotFoundError):
    print("❌ 未找到 buildozer，请先安装:")
    print("   pip install buildozer")
    print("   并确保 Java 17 + Android SDK/NDK 已配置")
    sys.exit(1)

# 执行打包
cmd = ["buildozer", "android", MODE]
print(f"执行: {' '.join(cmd)}")
print("（首次运行会下载 Android SDK/NDK，可能需要 10-30 分钟）")
print()

result = subprocess.run(cmd)
if result.returncode == 0:
    # 找 APK
    import glob
    apks = glob.glob("bin/*.apk")
    if apks:
        print(f"\n✅ APK 已生成: {apks[0]}")
        print(f"   大小: {os.path.getsize(apks[0]) / 1024 / 1024:.1f} MB")
    else:
        print("\n⚠️ 打包成功但未找到 APK 文件，请检查 bin/ 目录")
else:
    print(f"\n❌ 打包失败 (exit code {result.returncode})")
    print("查看上方日志排查错误")
