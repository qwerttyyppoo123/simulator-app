[app]

# 应用标题（手机上显示的名字）
title = 自定义模拟器

# 包名（必须唯一，用反向域名格式）
package.name = customsim

# 包域名
package.domain = com.customsim

# 源代码入口
source.dir = .
source.include_exts = py,png,jpg,kv,json
source.exclude_exts = spec
source.exclude_dirs = tests, bin, obj

# 主程序文件
main.py = main.py

# 版本
version = 1.0.0

# 应用要求
requirements = python3,kivy==2.3.0

# 横竖屏：both = 都支持（你要求的"可变化"）
orientation = both

# 全屏模式（隐藏状态栏）
fullscreen = 0

# Android API 配置（兼容 Android 7.0+）
android.api = 33
android.minapi = 24
android.ndk = 25b
android.sdk = 33

# 权限（文件读写存档需要）
android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# 状态栏颜色（尽量还原桌面版风格）
android.bar_color = #f0f0f0
android.bar_text_color = #1a1a1a

# 图标（放在同目录下的 icon.png，建议 512x512）
icon.filename = icon.png

# 启动图
presplash.filename = presplash.png
presplash.color = #ffffff

# 支持的设备
android.archs = arm64-v8a,armeabi-v7a

# 是否包含调试信息
android.release = true

# 日志
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
