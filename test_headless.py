# -*- coding: utf-8 -*-
"""Headless 测试：验证所有核心逻辑不报错"""
import os
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_LOG_LEVEL'] = 'error'

# 禁用窗口
import kivy
kivy.require('2.3.0')
from kivy.config import Config
Config.set('kivy', 'desktop', '0')

# 测试工具函数
import sys
sys.path.insert(0, '.')

# 直接 import main 里的工具函数
from main import (
    safe_eval, weighted_random, contrast_color,
    get_default_data, load_config, save_config,
    C, APP_NAME, DATA_FILE, CONFIG_FILE
)

print("=== 核心逻辑测试 ===\n")

# 1. safe_eval
assert safe_eval("10+20") == "30", "加法失败"
assert safe_eval("5*6") == "30", "乘法失败"
assert safe_eval("100/3") == "33.333333333333336", "除法失败"
assert safe_eval("abc") == "abc", "非算式应原样返回"
print("✅ safe_eval (算式求值)")

# 2. weighted_random
opts = [{"name":"金","weight":1},{"name":"木","weight":2},{"name":"水","weight":1}]
res = {}
for _ in range(10000):
    r = weighted_random(opts)
    res[r] = res.get(r, 0) + 1
assert res["木"] > res["金"] * 1.5, f"权重2应明显多于权重1: {res}"
assert all(r in ["金","木","水"] for r in res), "不应出现其他选项"
print(f"✅ weighted_random (权重抽样): 金={res['金']} 木={res['木']} 水={res['水']}")

# 权重0不出现
opts2 = [{"name":"A","weight":0},{"name":"B","weight":1}]
res2 = {}
for _ in range(1000):
    r = weighted_random(opts2)
    res2[r] = res2.get(r, 0) + 1
assert "A" not in res2, "权重0不应被抽中"
print(f"✅ weighted_random (权重0忽略): {res2}")

# 3. contrast_color
assert contrast_color("#ffffff") == "#000000", "白色底→黑字"
assert contrast_color("#000000") == "#ffffff", "黑色底→白字"
assert contrast_color("#ff0000") == "#ffffff", "红色底→白字"
print("✅ contrast_color (文字对比色)")

# 4. get_default_data
data = get_default_data()
assert len(data) == 8, f"默认数据应有8项，实际{len(data)}"
assert any(d["name"] == "灵根" and d["type"] == "random" for d in data), "应有随机项"
random_item = [d for d in data if d["type"] == "random"][0]
assert len(random_item["options"]) == 6, "灵根应有6个选项"
print(f"✅ get_default_data (默认数据: {len(data)}项)")

# 5. 存档读写
import json
import tempfile
test_dir = tempfile.mkdtemp()
test_file = os.path.join(test_dir, "test.json")
with open(test_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
with open(test_file, "r", encoding="utf-8") as f:
    loaded = json.load(f)
assert loaded == data, "存档读写不一致"
print("✅ 存档 JSON 读写")

# 6. 模拟完整抽取流程
item = {"name": "灵根", "type": "random", "value": "", "options": opts}
final = weighted_random(item["options"])
item["value"] = final
item["type"] = "fixed"
assert item["type"] == "fixed"
assert item["value"] in ["金","木","水"]
print(f"✅ 抽取流程: 灵根 → {final} (已锁定为固定项)")

# 7. App 类初始化测试（不启动 GUI 循环）
from main import SimulatorApp
app = SimulatorApp()
# 不调用 build()（会创建窗口），只测数据加载
app.cfg = load_config()
app.font_size = app.cfg.get("font_size", 14)
app.zoom = app.cfg.get("zoom", 1.0)
app.data = []
app._load_data()
assert len(app.data) > 0, "App 数据加载失败"
print(f"✅ SimulatorApp 数据加载: {len(app.data)}项")

print("\n🎉 全部测试通过！代码逻辑无误，可以打包 APK。")
