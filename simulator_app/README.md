# 自定义模拟器 - Android 版

基于 Kivy 框架的跨平台应用，由原 Tkinter 桌面版完整移植。

## 📱 功能说明

| 功能 | 说明 |
|------|------|
| 🔒 固定项 | 不可计算的固定数值（如姓名、种族） |
| ✏️ 变动项 | 可计算数值，支持 + - * / 算式，含快捷按钮 |
| 🎲 随机项 | 按权重随机抽取，3秒匀速滚动动画，锁定后变固定项 |
| 🎨 行颜色 | 每行可自定义背景色，文字色自动适配 |
| 📂 存档 | JSON 格式读写，支持多存档文件 |
| 📐 横竖屏 | 自适应，切换自动重排版面 |
| ⚙️ 随机选项 | 右键(长按)设置名称+权重，支持预设 |

## 🏗️ 项目结构

```
simulator_app/
├── main.py              # 主程序（1650行，纯 Python）
├── buildozer.spec       # APK 打包配置
├── icon.png             # 应用图标 512x512
├── presplash.png        # 启动闪屏图 1080x1920
├── gen_assets.py        # 图标/闪屏生成脚本
├── pack_apk.py          # 一键打包脚本
└── README.md            # 本文件
```

## 🚀 打包 APK（在 Linux/macOS 上操作）

### 1. 安装依赖 (Ubuntu 22.04 为例)

```bash
sudo apt update
sudo apt install -y python3-pip python3-setuptools
sudo apt install -y git zip unzip openjdk-17-jdk
sudo apt install -y autoconf libtool pkg-config
pip3 install --user buildozer
export PATH=$PATH:~/.local/bin
```

### 2. 打包

```bash
cd simulator_app

# Debug 包（可直接安装测试）
buildozer android debug

# Release 包（需配置签名）
buildozer android release
```

> 首次运行会下载 Android SDK + NDK（约 2GB），需 10-30 分钟。

### 3. 获取 APK

打包完成后：
- Debug: `bin/customsim-1.0.0-debug.apk`
- Release: `bin/customsim-1.0.0-release.apk`

传到手机安装即可。

## 🖥️ 桌面端测试（无需打包）

```bash
pip install kivy
python main.py
```

支持 Windows / macOS / Linux 直接运行，方便开发调试。

## 🎮 操作说明

| 操作 | 效果 |
|------|------|
| 点击数值列 | 编辑数值（变动项）/ 触发抽取（随机项） |
| 点击名称列 | 修改名称 |
| **长按任意行 0.5秒** | 弹出操作菜单（修改/删除/颜色/随机选项） |
| 滑动 | 滚动列表 |
| 横竖屏切换 | 自动重排（竖屏表格紧凑，横屏更宽裕） |

## ⚙️ buildozer.spec 关键配置

```ini
orientation = both          # 横竖屏都支持
android.api = 33            # 适配 Android 13
android.minapi = 24         # 最低 Android 7.0
android.release = true      # 发布模式
android.archs = arm64-v8a   # 支持 64 位（也兼容 32 位）
```

## 📝 与桌面版的区别

| 项目 | 桌面版 (Tkinter) | Android 版 (Kivy) |
|------|-----------------|-------------------|
| 界面风格 | Windows 原生 | Material 扁平风（色调保持一致） |
| 右键菜单 | 鼠标右键 | **长按 0.5 秒** |
| 弹窗 | Toplevel 窗口 | ModalView 弹层 |
| 颜色选择 | 独立窗口 | 弹层内网格 |
| 存档路径 | exe 同目录 | app 私有目录 |
| 字号缩放 | Scale 滑块 | 工具栏滑块 |

## 🔧 常见问题

**Q: 打包时提示 Java 版本不对？**
A: 需要 JDK 17。Ubuntu: `sudo apt install openjdk-17-jdk`

**Q: APK 安装后闪退？**
A: 检查 Android 版本 ≥ 7.0。用 `adb logcat` 看崩溃日志。

**Q: 怎么换图标？**
A: 替换 `icon.png`（512x512 PNG），重新打包即可。

**Q: 能加新功能吗？**
A: 直接改 `main.py`，Kivy 支持热重载开发。
