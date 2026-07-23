# -*- coding: utf-8 -*-
"""
快速启动脚本 - 双击或在终端运行即可启动应用
"""
import os
import sys

# 确保能找到 main.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import SimulatorApp

if __name__ == "__main__":
    SimulatorApp().run()
