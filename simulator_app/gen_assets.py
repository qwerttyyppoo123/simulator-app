# -*- coding: utf-8 -*-
"""生成图标和启动图"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT = os.path.dirname(os.path.abspath(__file__))

# ===== 图标 512x512 =====
icon = Image.new("RGB", (512, 512), "#e65100")
d = ImageDraw.Draw(icon)

# 圆角矩形背景
d.rounded_rectangle([20, 20, 492, 492], radius=60, fill="#e65100")

# 骰子图案（简化版 - 用圆点表示）
# 大圆点
d.ellipse([180, 100, 332, 252], fill="#ffffff")  # 上
d.ellipse([180, 260, 332, 412], fill="#ffffff")  # 下

# 小圆点装饰
for cx, cy in [(120, 140), (392, 140), (120, 372), (392, 372), (256, 256)]:
    r = 18
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill="#ffb300")

# 文字
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 48)
except:
    font = ImageFont.load_default()

text = "模拟器"
bbox = d.textbbox((0,0), text, font=font)
tw = bbox[2] - bbox[0]
d.text(((512-tw)//2, 420), text, fill="#ffffff", font=font)

icon.save(os.path.join(OUT, "icon.png"), "PNG")
print("✅ icon.png 已生成 (512x512)")

# ===== 启动图 1080x1920 =====
sp = Image.new("RGB", (1080, 1920), "#ffffff")
d2 = ImageDraw.Draw(sp)

# 顶部装饰条
d2.rectangle([0, 0, 1080, 120], fill="#e65100")

# 中间大骰子
cx, cy = 540, 800
size = 200
d2.rounded_rectangle([cx-size, cy-size, cx+size, cy+size], radius=30, fill="#fff8e1", outline="#e65100", width=4)
# 点数
for dx, dy in [(-90, -90), (90, -90), (0, 0), (-90, 90), (90, 90)]:
    r = 16
    d2.ellipse([cx+dx-r, cy+dy-r, cx+dx+r, cy+dy+r], fill="#e65100")

# 标题
try:
    fbig = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 72)
    fsmall = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc", 36)
except:
    fbig = ImageFont.load_default()
    fsmall = ImageFont.load_default()

title = "自定义模拟器"
bbox = d2.textbbox((0,0), title, font=fbig)
tw = bbox[2] - bbox[0]
d2.text(((1080-tw)//2, 1050), title, fill="#1a1a1a", font=fbig)

sub = "加载中..."
bbox2 = d2.textbbox((0,0), sub, font=fsmall)
tw2 = bbox2[2] - bbox2[0]
d2.text(((1080-tw2)//2, 1150), sub, fill="#888888", font=fsmall)

# 底部装饰
d2.rectangle([0, 1800, 1080, 1920], fill="#f0f0f0")
d2.text((40, 1840), "左键点击随机项 → 抽取", fill="#888888", font=fsmall)
d2.text((40, 1880), "长按任意行 → 操作菜单", fill="#888888", font=fsmall)

sp.save(os.path.join(OUT, "presplash.png"), "PNG")
print("✅ presplash.png 已生成 (1080x1920)")

print("\n所有资源生成完毕！")
