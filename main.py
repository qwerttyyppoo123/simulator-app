# -*- coding: utf-8 -*-
"""
自定义模拟器 - Android 版 (Kivy)
功能完全对标桌面版 v5.4：
- 固定项 / 变动项 / 随机项
- 左键点击随机项 → 3秒匀速滚动 → 锁定 → 变固定项
- 右键(长按)菜单：修改数值/名称/颜色/随机选项
- 横竖屏自适应
- 存档 JSON 读写
"""

import os
import json
import random
import time

# ============ Kivy 环境初始化（必须在最前面）============
os.environ.setdefault('KIVY_GL_BACKEND', 'sdl2')
os.environ.setdefault('KIVY_WINDOW', 'sdl2')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.progressbar import ProgressBar
from kivy.uix.filechooser import FileChooserListView
from kivy.properties import (
    StringProperty, NumericProperty, ListProperty,
    ObjectProperty, BooleanProperty, DictProperty
)
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.utils import get_color_from_hex
from kivy.core.window import Window
from kivy.lang import Builder

# ============ 全局配置 ============
APP_NAME = "自定义模拟器"
CONFIG_FILE = "config.json"
DATA_FILE = "data.json"

# 颜色方案（尽量还原桌面版）
C = {
    "bg": "#ffffff", "bg_alt": "#f5f5f5", "bg_dark": "#e8e8e8",
    "bg_toolbar": "#f0f0f0", "bg_table": "#ffffff",
    "text": "#1a1a1a", "text_dim": "#888888",
    "border": "#cccccc", "border_dark": "#999999",
    "accent": "#333333", "btn_bg": "#e0e0e0", "btn_hover": "#cccccc",
    "btn_dark": "#444444", "white": "#ffffff", "black": "#000000",
    "red": "#cc0000", "green": "#2e7d32", "orange": "#e65100",
    "random_bg": "#fff8e1", "random_border": "#ffb300",
    "row_selected": "#d0d0d0",
}

# 存档目录：Android 上用 app 私有目录
from kivy.app import App
from kivy.utils import platform
if platform == 'android':
    from android.storage import app_storage_path
    BASE_DIR = app_storage_path()
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SAVE_FOLDER = os.path.join(BASE_DIR, "存档")
os.makedirs(SAVE_FOLDER, exist_ok=True)


# ============ 工具函数 ============
def safe_eval(expr):
    """安全求值，支持 + - * / 算式"""
    try:
        allowed = set("0123456789.+-*/ ")
        if not all(c in allowed for c in expr):
            return expr
        result = eval(expr, {"__builtins__": None}, {})
        if isinstance(result, float) and result.is_integer():
            return str(int(result))
        return str(result)
    except:
        return expr


def weighted_random(options):
    """按权重随机抽取"""
    if not options:
        return None
    names = [o["name"] for o in options]
    weights = [max(int(o.get("weight", 1)), 0) for o in options]
    total = sum(weights)
    if total <= 0:
        return random.choice(names)
    return random.choices(names, weights=weights, k=1)[0]


def contrast_color(hex_color):
    """根据背景色亮度返回黑/白文字色"""
    try:
        h = hex_color.lstrip('#')
        r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        return "#000000" if lum > 140 else "#ffffff"
    except:
        return "#000000"


def ensure_save_folder():
    if not os.path.exists(SAVE_FOLDER):
        os.makedirs(SAVE_FOLDER)


def load_config():
    try:
        path = os.path.join(BASE_DIR, CONFIG_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {"font_size": 14, "zoom": 1.0}


def save_config(cfg):
    try:
        path = os.path.join(BASE_DIR, CONFIG_FILE)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except:
        pass


# ============ 默认数据 ============
def get_default_data():
    return [
        {"name": "姓名", "type": "fixed", "value": "韩立", "color": "#f0f0f0"},
        {"name": "种族", "type": "fixed", "value": "人族", "color": "#f0f0f0"},
        {"name": "境界", "type": "fixed", "value": "炼气期", "color": "#f0f0f0"},
        {"name": "灵根", "type": "random", "value": "", "color": "#fff8e1",
         "options": [{"name":"金灵根","weight":1},{"name":"木灵根","weight":1},
                     {"name":"水灵根","weight":1},{"name":"火灵根","weight":1},
                     {"name":"土灵根","weight":1},{"name":"天灵根","weight":1}]},
        {"name": "寿元", "type": "dynamic", "value": "80", "color": "#ffffff"},
        {"name": "修为", "type": "dynamic", "value": "0", "color": "#ffffff"},
        {"name": "战力", "type": "dynamic", "value": "10", "color": "#ffffff"},
        {"name": "灵石", "type": "dynamic", "value": "50", "color": "#ffffff"},
    ]


# ============ 随机抽取弹窗 ============
class RollPopup(ModalView):
    """随机抽取动画弹窗 - 匀速3秒"""

    def __init__(self, item_name, options, on_result, **kwargs):
        super().__init__(**kwargs)
        self.item_name = item_name
        self.options = list(options)
        self.on_result = on_result
        self.roll_count = 0
        self.max_rolls = 60  # 60 * 50ms = 3秒
        self.final_result = weighted_random(self.options)
        self.rolling = False

        self.size_hint = (0.85, 0.45)
        self.auto_dismiss = False
        self.background_color = get_color_from_hex(C["random_bg"]) + [1]

        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(16))

        # 标题栏
        title_bar = BoxLayout(size_hint=(1, 0.2), orientation="horizontal")
        title_label = Label(
            text=f"🎲 {self.item_name}",
            font_size=sp(18), bold=True,
            color=get_color_from_hex("#ffffff"),
            size_hint=(1, 1),
            halign="left", valign="middle"
        )
        title_label.bind(size=title_label.setter('text_size'))
        title_bar.add_widget(title_label)
        root.add_widget(title_bar)

        # 显示区
        self.display = Label(
            text="?",
            font_size=sp(32), bold=True,
            color=get_color_from_hex(C["orange"]),
            size_hint=(1, 0.5),
            halign="center", valign="middle"
        )
        self.display.bind(size=self.display.setter('text_size'))
        root.add_widget(self.display)

        # 状态
        self.status_label = Label(
            text="点击下方按钮开始抽取",
            font_size=sp(12),
            color=get_color_from_hex(C["text_dim"]),
            size_hint=(1, 0.15)
        )
        root.add_widget(self.status_label)

        # 按钮区
        btn_row = BoxLayout(size_hint=(1, 0.2), spacing=dp(10))
        self.roll_btn = Button(
            text="🎲 开始抽取",
            font_size=sp(14), bold=True,
            background_color=get_color_from_hex(C["orange"]),
            color=get_color_from_hex("#ffffff"),
        )
        self.roll_btn.bind(on_release=self.start_roll)
        btn_row.add_widget(self.roll_btn)

        cancel_btn = Button(
            text="取消",
            font_size=sp(13),
            background_color=get_color_from_hex(C["btn_bg"]),
            color=get_color_from_hex(C["text"]),
        )
        cancel_btn.bind(on_release=self.do_cancel)
        btn_row.add_widget(cancel_btn)

        root.add_widget(btn_row)
        self.add_widget(root)

    def start_roll(self, *args):
        if self.rolling:
            return
        self.rolling = True
        self.roll_count = 0
        self.roll_btn.disabled = True
        self.roll_btn.text = "抽取中..."
        self._tick()

    def _tick(self, *args):
        if self.roll_count >= self.max_rolls:
            self.display.text = self.final_result
            self.display.color = get_color_from_hex(C["green"])
            self.status_label.text = "✅ 结果已锁定 → 该项将变为固定项"
            self.status_label.color = get_color_from_hex(C["green"])
            self.roll_btn.disabled = False
            self.roll_btn.text = "✔ 确认"
            self.roll_btn.background_color = get_color_from_hex(C["green"])
            self.roll_btn.unbind(on_release=self.start_roll)
            self.roll_btn.bind(on_release=self.do_confirm)
            return

        names = [o["name"] for o in self.options]
        show = random.choice(names)
        self.display.text = show
        self.roll_count += 1
        Clock.schedule_once(self._tick, 0.05)  # 50ms 固定间隔

    def do_confirm(self, *args):
        self.on_result(self.final_result)
        self.dismiss()

    def do_cancel(self, *args):
        self.on_result(None)
        self.dismiss()


# ============ 添加/编辑属性弹窗 ============
class AddItemPopup(ModalView):
    """添加新属性弹窗"""

    def __init__(self, on_confirm, default_type="dynamic", edit_data=None, **kwargs):
        super().__init__(**kwargs)
        self.on_confirm = on_confirm
        self.selected_color = "#ffffff"
        self.options_list = []
        self.edit_data = edit_data  # 如果是编辑模式，传现有数据

        self.size_hint = (0.95, 0.92)
        self.auto_dismiss = False
        self.background_color = get_color_from_hex(C["bg"]) + [1]

        self._build_ui()

        if edit_data:
            self._fill_edit_data()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(14))

        # 标题
        title = Label(
            text="➕ 添加新属性" if not self.edit_data else "✏️ 编辑属性",
            font_size=sp(16), bold=True,
            color=get_color_from_hex(C["text"]),
            size_hint=(1, 0.06),
            halign="left"
        )
        title.bind(size=title.setter('text_size'))
        root.add_widget(title)

        # 滚动区
        scroll = ScrollView(size_hint=(1, 0.82))
        body = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        body.bind(minimum_height=body.setter('height'))

        # === 名称 ===
        body.add_widget(self._section_label("属性名称"))
        name_row = BoxLayout(size_hint_y=None, height=dp(40))
        self.name_input = TextInput(
            text="", multiline=False,
            font_size=sp(14),
            background_color=get_color_from_hex("#ffffff"),
            foreground_color=get_color_from_hex(C["text"]),
            hint_text="输入属性名称...",
            size_hint=(1, 1)
        )
        name_row.add_widget(self.name_input)
        body.add_widget(name_row)

        # === 类型 ===
        body.add_widget(self._section_label("属性类型"))
        type_row = BoxLayout(size_hint_y=None, height=dp(36))
        self.type_spinner = Spinner(
            text="变动数值（可计算）",
            values=["固定数值（不可计算）", "变动数值（可计算）", "随机项（按权重抽取）"],
            font_size=sp(13),
            background_color=get_color_from_hex(C["bg_alt"]),
            color=get_color_from_hex(C["text"]),
            size_hint=(1, 1)
        )
        self.type_spinner.bind(text=self._on_type_change)
        type_row.add_widget(self.type_spinner)
        body.add_widget(type_row)

        # === 初始数值（固定/变动）===
        self.value_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        self.value_container.add_widget(self._section_label("初始数值"))
        val_row = BoxLayout(size_hint_y=None, height=dp(40))
        self.value_input = TextInput(
            text="0", multiline=False,
            font_size=sp(14),
            background_color=get_color_from_hex("#ffffff"),
            foreground_color=get_color_from_hex(C["text"]),
            hint_text="输入初始数值...",
            size_hint=(1, 1)
        )
        val_row.add_widget(self.value_input)
        self.value_container.add_widget(val_row)
        body.add_widget(self.value_container)

        # === 随机选项区 ===
        self.random_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4), padding=(0, 0, 0, dp(8)))
        self.random_container.add_widget(self._section_label("随机选项（名称 + 权重）", color=C["orange"]))
        hint = Label(
            text="权重越大越容易被抽中，0表示永远不抽中",
            font_size=sp(10), color=get_color_from_hex(C["text_dim"]),
            size_hint_y=None, height=dp(18), halign="left"
        )
        hint.bind(size=hint.setter('text_size'))
        self.random_container.add_widget(hint)

        # 选项列表
        self.opt_scroll = ScrollView(size_hint_y=None, height=dp(120))
        self.opt_list = BoxLayout(orientation="vertical", spacing=dp(2), size_hint_y=None)
        self.opt_list.bind(minimum_height=self.opt_list.setter('height'))
        self.opt_scroll.add_widget(self.opt_list)
        self.random_container.add_widget(self.opt_scroll)

        # 添加选项行
        add_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(4))
        add_row.add_widget(Label(text="名称:", font_size=sp(12), color=get_color_from_hex(C["text"]), size_hint=(0.15, 1)))
        self.opt_name_input = TextInput(text="", multiline=False, font_size=sp(12), size_hint=(0.4, 1))
        add_row.add_widget(self.opt_name_input)
        add_row.add_widget(Label(text="权重:", font_size=sp(12), color=get_color_from_hex(C["text"]), size_hint=(0.15, 1)))
        self.opt_weight_input = TextInput(text="1", multiline=False, font_size=sp(12), size_hint=(0.2, 1))
        add_row.add_widget(self.opt_weight_input)
        add_btn = Button(
            text="➕", font_size=sp(14),
            background_color=get_color_from_hex(C["btn_dark"]),
            color=get_color_from_hex("#ffffff"),
            size_hint=(0.15, 1)
        )
        add_btn.bind(on_release=self._add_option)
        add_row.add_widget(add_btn)
        self.random_container.add_widget(add_row)

        # 预设
        preset_row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(4))
        preset_row.add_widget(Label(text="预设:", font_size=sp(10), color=get_color_from_hex(C["text_dim"]), size_hint=(0.2, 1)))
        for label, opts in [("男/女", [("男",1),("女",1)]), ("优/良/中/差", [("优秀",1),("良好",2),("中等",3),("较差",1)])]:
            b = Button(text=label, font_size=sp(10),
                       background_color=get_color_from_hex(C["bg_alt"]),
                       color=get_color_from_hex(C["text"]),
                       size_hint=(0.3, 1))
            b.bind(on_release=lambda x, o=opts: self._apply_preset(o))
            preset_row.add_widget(b)
        self.random_container.add_widget(preset_row)

        body.add_widget(self.random_container)

        # === 行颜色 ===
        body.add_widget(self._section_label("行颜色（点击选择）"))
        color_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        self.color_btn = Button(
            text="    ",
            background_color=get_color_from_hex("#ffffff"),
            size_hint=(0.15, 1)
        )
        self.color_btn.bind(on_release=self._pick_color)
        color_row.add_widget(self.color_btn)
        color_row.add_widget(Label(
            text="← 点击选色（不选=默认白）",
            font_size=sp(11), color=get_color_from_hex(C["text_dim"]),
            size_hint=(0.85, 1), halign="left"
        ))
        body.add_widget(color_row)

        scroll.add_widget(body)
        root.add_widget(scroll)

        # === 底部按钮 ===
        btn_row = BoxLayout(size_hint=(1, 0.08), spacing=dp(10), padding=(0, dp(4)))
        cancel_btn = Button(
            text="取消", font_size=sp(13),
            background_color=get_color_from_hex(C["btn_bg"]),
            color=get_color_from_hex(C["text"]),
            size_hint=(0.3, 1)
        )
        cancel_btn.bind(on_release=self.dismiss)
        btn_row.add_widget(cancel_btn)

        ok_btn = Button(
            text="✔ 确认添加" if not self.edit_data else "✔ 保存修改",
            font_size=sp(14), bold=True,
            background_color=get_color_from_hex(C["btn_dark"]),
            color=get_color_from_hex("#ffffff"),
            size_hint=(0.4, 1)
        )
        ok_btn.bind(on_release=self._on_ok)
        btn_row.add_widget(ok_btn)

        root.add_widget(btn_row)
        self.add_widget(root)

        # 默认隐藏随机区
        self.random_container.height = 0
        self.random_container.opacity = 0
        self._type_map = {
            "固定数值（不可计算）": "fixed",
            "变动数值（可计算）": "dynamic",
            "随机项（按权重抽取）": "random",
        }

    def _section_label(self, text, color=None):
        c = color or C["text"]
        return Label(
            text=text, font_size=sp(12), bold=True,
            color=get_color_from_hex(c),
            size_hint_y=None, height=dp(22),
            halign="left", valign="bottom"
        )

    def _on_type_change(self, spinner, text):
        t = self._type_map.get(text, "dynamic")
        if t == "random":
            self.value_container.height = 0
            self.value_container.opacity = 0
            self.random_container.height = dp(220)
            self.random_container.opacity = 1
        else:
            self.random_container.height = 0
            self.random_container.opacity = 0
            self.value_container.height = dp(70)
            self.value_container.opacity = 1

    def _add_option(self, *args):
        name = self.opt_name_input.text.strip()
        if not name:
            return
        try:
            w = max(int(self.opt_weight_input.text.strip()), 0)
        except:
            w = 1
        self.options_list.append({"name": name, "weight": w})
        self.opt_name_input.text = ""
        self.opt_weight_input.text = "1"
        self._refresh_options()
        self.opt_name_input.focus = True

    def _apply_preset(self, opts):
        self.options_list = [{"name": n, "weight": w} for n, w in opts]
        self._refresh_options()

    def _refresh_options(self):
        self.opt_list.clear_widgets()
        for i, opt in enumerate(self.options_list):
            row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(4))
            row.add_widget(Label(
                text=f"  {opt['name']} (权重 {opt['weight']})",
                font_size=sp(11), color=get_color_from_hex(C["text"]),
                size_hint=(0.7, 1), halign="left"
            ))
            del_btn = Button(
                text="🗑️", font_size=sp(11),
                background_color=get_color_from_hex(C["bg_alt"]),
                size_hint=(0.15, 1)
            )
            del_btn.bind(on_release=lambda x, idx=i: self._del_option(idx))
            row.add_widget(del_btn)
            self.opt_list.add_widget(row)

    def _del_option(self, idx):
        if 0 <= idx < len(self.options_list):
            del self.options_list[idx]
            self._refresh_options()

    def _pick_color(self, *args):
        """弹出颜色选择网格"""
        picker = ModalView(size_hint=(0.9, 0.55), auto_dismiss=True)
        picker.background_color = get_color_from_hex(C["bg"]) + [1]
        layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))

        # 预设颜色网格
        colors = [
            "#FFFFFF","#F5F5F5","#E0E0E0","#CCCCCC","#FFEBEE",
            "#FCE4EC","#F3E5F5","#EDE7F6","#E3F2FD","#E8F5E9",
            "#F1F8E9","#F9FBE7","#FFFDE7","#FFF3E0","#FFCDD2",
            "#EF9A9A","#BBDEFB","#90CAF9","#C8E6C9","#A5D6A7",
            "#FFE0B2","#D7CCC8","#CFD8DC","#B0BEC5","#EEEEEE",
        ]
        grid = GridLayout(cols=5, spacing=dp(4), size_hint_y=None, height=dp(200))
        for c in colors:
            btn = Button(
                background_color=get_color_from_hex(c),
                size_hint=(1, None), height=dp(36)
            )
            btn.bind(on_release=lambda x, col=c: self._set_color(col, picker))
            grid.add_widget(btn)
        layout.add_widget(grid)

        # 自定义输入
        custom_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        custom_row.add_widget(Label(text="自定义:", font_size=sp(11), color=get_color_from_hex(C["text"]), size_hint=(0.25, 1)))
        self.custom_color_input = TextInput(
            text=self.selected_color, multiline=False,
            font_size=sp(12), size_hint=(0.45, 1)
        )
        custom_row.add_widget(self.custom_color_input)
        set_btn = Button(
            text="确定", font_size=sp(12),
            background_color=get_color_from_hex(C["btn_dark"]),
            color=get_color_from_hex("#ffffff"),
            size_hint=(0.2, 1)
        )
        set_btn.bind(on_release=lambda x: self._set_color(self.custom_color_input.text.strip(), picker))
        custom_row.add_widget(set_btn)
        layout.add_widget(custom_row)

        picker.add_widget(layout)
        picker.open()

    def _set_color(self, color, picker):
        if not color.startswith("#"):
            color = "#" + color
        if len(color) == 7:
            self.selected_color = color
            self.color_btn.background_color = get_color_from_hex(color)
        picker.dismiss()

    def _on_ok(self, *args):
        name = self.name_input.text.strip()
        if not name:
            return
        t = self._type_map.get(self.type_spinner.text, "dynamic")

        if t == "random":
            if not self.options_list:
                return
            result = {
                "name": name, "type": "random",
                "value": "",
                "color": self.selected_color,
                "options": list(self.options_list),
            }
        else:
            result = {
                "name": name, "type": t,
                "value": self.value_input.text.strip() or "0",
                "color": self.selected_color,
            }

        self.on_confirm(result)
        self.dismiss()

    def _fill_edit_data(self):
        d = self.edit_data
        self.name_input.text = d.get("name", "")
        t = d.get("type", "dynamic")
        reverse_map = {"fixed": "固定数值（不可计算）", "dynamic": "变动数值（可计算）", "random": "随机项（按权重抽取）"}
        self.type_spinner.text = reverse_map.get(t, "变动数值（可计算）")
        self.value_input.text = str(d.get("value", "0"))
        self.selected_color = d.get("color", "#ffffff")
        self.color_btn.background_color = get_color_from_hex(self.selected_color)
        self.options_list = [dict(o) for o in d.get("options", [])]
        self._refresh_options()
        self._on_type_change(self.type_spinner, self.type_spinner.text)


# ============ 随机选项编辑弹窗 ============
class EditRandomOptionsPopup(ModalView):
    """编辑已有随机项的选项和权重"""

    def __init__(self, item_name, options, on_save, **kwargs):
        super().__init__(**kwargs)
        self.item_name = item_name
        self.options_list = [dict(o) for o in options]
        self.on_save = on_save

        self.size_hint = (0.9, 0.7)
        self.auto_dismiss = False
        self.background_color = get_color_from_hex(C["bg"]) + [1]

        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(14))

        root.add_widget(Label(
            text=f"⚙️ {self.item_name} 的随机选项",
            font_size=sp(15), bold=True,
            color=get_color_from_hex(C["text"]),
            size_hint=(1, 0.08), halign="left"
        ))

        root.add_widget(Label(
            text="权重越大越容易被抽中，0=永远不抽中",
            font_size=sp(10), color=get_color_from_hex(C["text_dim"]),
            size_hint=(1, 0.06), halign="left"
        ))

        # 列表
        scroll = ScrollView(size_hint=(1, 0.55))
        self.opt_list = BoxLayout(orientation="vertical", spacing=dp(3), size_hint_y=None)
        self.opt_list.bind(minimum_height=self.opt_list.setter('height'))
        scroll.add_widget(self.opt_list)
        root.add_widget(scroll)

        # 添加行
        add_row = BoxLayout(size_hint=(1, 0.1), spacing=dp(4))
        add_row.add_widget(Label(text="名称:", font_size=sp(12), color=get_color_from_hex(C["text"]), size_hint=(0.12, 1)))
        self.name_input = TextInput(text="", multiline=False, font_size=sp(12), size_hint=(0.35, 1))
        add_row.add_widget(self.name_input)
        add_row.add_widget(Label(text="权重:", font_size=sp(12), color=get_color_from_hex(C["text"]), size_hint=(0.12, 1)))
        self.weight_input = TextInput(text="1", multiline=False, font_size=sp(12), size_hint=(0.2, 1))
        add_row.add_widget(self.weight_input)
        add_btn = Button(text="➕ 添加", font_size=sp(12),
                         background_color=get_color_from_hex(C["btn_dark"]),
                         color=get_color_from_hex("#ffffff"), size_hint=(0.2, 1))
        add_btn.bind(on_release=self._add)
        add_row.add_widget(add_btn)
        root.add_widget(add_row)

        # 预设
        preset_row = BoxLayout(size_hint=(1, 0.08), spacing=dp(6))
        preset_row.add_widget(Label(text="预设:", font_size=sp(10), color=get_color_from_hex(C["text_dim"]), size_hint=(0.12, 1)))
        for label, opts in [("清空", []), ("男/女", [("男",1),("女",1)]), ("ABC", [("A",1),("B",1),("C",1)])]:
            b = Button(text=label, font_size=sp(10),
                       background_color=get_color_from_hex(C["bg_alt"]),
                       color=get_color_from_hex(C["text"]), size_hint=(0.2, 1))
            b.bind(on_release=lambda x, o=opts: self._preset(o))
            preset_row.add_widget(b)
        root.add_widget(preset_row)

        # 按钮
        btn_row = BoxLayout(size_hint=(1, 0.1), spacing=dp(10))
        cancel = Button(text="取消", font_size=sp(13),
                        background_color=get_color_from_hex(C["btn_bg"]),
                        color=get_color_from_hex(C["text"]), size_hint=(0.3, 1))
        cancel.bind(on_release=self.dismiss)
        btn_row.add_widget(cancel)
        save = Button(text="✔ 保存", font_size=sp(14), bold=True,
                      background_color=get_color_from_hex(C["btn_dark"]),
                      color=get_color_from_hex("#ffffff"), size_hint=(0.3, 1))
        save.bind(on_release=self._save)
        btn_row.add_widget(save)
        root.add_widget(btn_row)

        self.add_widget(root)
        self._refresh()

    def _add(self, *args):
        n = self.name_input.text.strip()
        try: w = max(int(self.weight_input.text.strip()), 0)
        except: w = 1
        if not n: return
        self.options_list.append({"name": n, "weight": w})
        self.name_input.text = ""
        self.weight_input.text = "1"
        self._refresh()

    def _preset(self, opts):
        if not opts:
            self.options_list = []
        else:
            self.options_list = [{"name": n, "weight": w} for n, w in opts]
        self._refresh()

    def _refresh(self):
        self.opt_list.clear_widgets()
        for i, o in enumerate(self.options_list):
            row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(4))
            row.add_widget(Label(
                text=f"  {o['name']}  权重:{o['weight']}",
                font_size=sp(11), color=get_color_from_hex(C["text"]),
                size_hint=(0.6, 1), halign="left"
            ))
            edit_btn = Button(text="✏️", font_size=sp(11), size_hint=(0.15, 1),
                              background_color=get_color_from_hex(C["bg_alt"]))
            edit_btn.bind(on_release=lambda x, idx=i: self._edit(idx))
            row.add_widget(edit_btn)
            del_btn = Button(text="🗑️", font_size=sp(11), size_hint=(0.15, 1),
                             background_color=get_color_from_hex(C["bg_alt"]))
            del_btn.bind(on_release=lambda x, idx=i: self._del(idx))
            row.add_widget(del_btn)
            self.opt_list.add_widget(row)

    def _edit(self, idx):
        if idx >= len(self.options_list): return
        old = self.options_list[idx]
        # 简单提示用 popup
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
        name_in = TextInput(text=old["name"], multiline=False, font_size=sp(13))
        content.add_widget(name_in)
        w_in = TextInput(text=str(old["weight"]), multiline=False, font_size=sp(13))
        content.add_widget(w_in)
        btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        ok = Button(text="确定", background_color=get_color_from_hex(C["btn_dark"]), color=get_color_from_hex("#ffffff"))
        cancel = Button(text="取消", background_color=get_color_from_hex(C["btn_bg"]), color=get_color_from_hex(C["text"]))
        btn_row.add_widget(cancel)
        btn_row.add_widget(ok)
        content.add_widget(btn_row)

        popup = ModalView(size_hint=(0.7, 0.3), auto_dismiss=False)
        popup.background_color = get_color_from_hex(C["bg"]) + [1]
        popup.add_widget(content)

        def do_ok(*a):
            self.options_list[idx] = {"name": name_in.text.strip(), "weight": int(w_in.text.strip() or 0)}
            self._refresh()
            popup.dismiss()

        ok.bind(on_release=do_ok)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _del(self, idx):
        if 0 <= idx < len(self.options_list):
            del self.options_list[idx]
            self._refresh()

    def _save(self, *args):
        self.on_save(list(self.options_list))
        self.dismiss()


# ============ 修改数值弹窗 ============
class EditValuePopup(ModalView):
    """修改变动项数值（支持算式预览）"""

    def __init__(self, item_name, current_value, on_confirm, **kwargs):
        super().__init__(**kwargs)
        self.item_name = item_name
        self.current_value = str(current_value)
        self.on_confirm = on_confirm

        self.size_hint = (0.9, 0.4)
        self.auto_dismiss = False
        self.background_color = get_color_from_hex(C["bg"]) + [1]

        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(14))

        root.add_widget(Label(
            text=f"✏️ {self.item_name}",
            font_size=sp(15), bold=True,
            color=get_color_from_hex(C["text"]),
            size_hint=(1, 0.15), halign="left"
        ))

        root.add_widget(Label(
            text=f"当前: {self.current_value}",
            font_size=sp(13),
            color=get_color_from_hex(C["text_dim"]),
            size_hint=(1, 0.12), halign="left"
        ))

        root.add_widget(Label(
            text="输入新数值或算式 (+ - * /)",
            font_size=sp(10), color=get_color_from_hex(C["text_dim"]),
            size_hint=(1, 0.08), halign="left"
        ))

        self.entry = TextInput(
            text=self.current_value, multiline=False,
            font_size=sp(16),
            background_color=get_color_from_hex("#ffffff"),
            foreground_color=get_color_from_hex(C["text"]),
            size_hint=(1, 0.2)
        )
        self.entry.bind(text=self._on_change)
        root.add_widget(self.entry)

        self.preview_label = Label(
            text="预览: —",
            font_size=sp(13), bold=True,
            color=get_color_from_hex(C["text_dim"]),
            size_hint=(1, 0.12), halign="left"
        )
        root.add_widget(self.preview_label)

        # 快捷按钮
        qf = BoxLayout(size_hint=(1, 0.15), spacing=dp(6))
        qf.add_widget(Label(text="快捷:", font_size=sp(11), color=get_color_from_hex(C["text_dim"]), size_hint=(0.15, 1)))
        for label, expr in [("+10", "+10"), ("+100", "+100"), ("×2", "*2"), ("÷2", "/2")]:
            b = Button(text=label, font_size=sp(11),
                       background_color=get_color_from_hex(C["bg_alt"]),
                       color=get_color_from_hex(C["text"]), size_hint=(0.2, 1))
            b.bind(on_release=lambda x, e=expr: self._quick(e))
            qf.add_widget(b)
        root.add_widget(qf)

        # 按钮
        btn_row = BoxLayout(size_hint=(1, 0.15), spacing=dp(10))
        cancel = Button(text="取消", font_size=sp(13),
                        background_color=get_color_from_hex(C["btn_bg"]),
                        color=get_color_from_hex(C["text"]))
        cancel.bind(on_release=self.dismiss)
        btn_row.add_widget(cancel)
        ok = Button(text="✔ 确认", font_size=sp(14), bold=True,
                    background_color=get_color_from_hex(C["btn_dark"]),
                    color=get_color_from_hex("#ffffff"))
        ok.bind(on_release=self._on_ok)
        btn_row.add_widget(ok)
        root.add_widget(btn_row)

        self.add_widget(root)
        Clock.schedule_once(lambda dt: setattr(self.entry, 'focus', True), 0.1)

    def _quick(self, expr):
        self.entry.text = self.current_value + expr
        self._on_change()

    def _on_change(self, *args):
        t = self.entry.text.strip()
        if not t:
            self.preview_label.text = "预览: —"
            self.preview_label.color = get_color_from_hex(C["text_dim"])
            return
        r = safe_eval(t)
        if r != t:
            self.preview_label.text = f"预览: {r}"
            self.preview_label.color = get_color_from_hex(C["text"])
        else:
            self.preview_label.text = f"原样: {t}"
            self.preview_label.color = get_color_from_hex(C["text_dim"])

    def _on_ok(self, *args):
        t = self.entry.text.strip()
        if not t:
            return
        self.on_confirm(safe_eval(t))
        self.dismiss()


# ============ 颜色选择弹窗（通用）============
class ColorPickerPopup(ModalView):
    """颜色选择器"""

    def __init__(self, current_color, on_select, **kwargs):
        super().__init__(**kwargs)
        self.current_color = current_color
        self.on_select = on_select

        self.size_hint = (0.85, 0.5)
        self.auto_dismiss = True
        self.background_color = get_color_from_hex(C["bg"]) + [1]

        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))

        # 预览
        self.preview = Button(
            text=self.current_color,
            background_color=get_color_from_hex(self.current_color),
            color=get_color_from_hex(contrast_color(self.current_color)),
            font_size=sp(14), bold=True,
            size_hint=(1, 0.2)
        )
        root.add_widget(self.preview)

        # 颜色网格
        colors = [
            "#FFFFFF","#F5F5F5","#E0E0E0","#CCCCCC","#B0B0B0",
            "#FFEBEE","#FCE4EC","#F3E5F5","#EDE7F6","#E3F2FD",
            "#E8F5E9","#F1F8E9","#F9FBE7","#FFFDE7","#FFF3E0",
            "#FFCDD2","#EF9A9A","#E57373","#BBDEFB","#90CAF9",
            "#64B5F6","#42A5F5","#C8E6C9","#A5D6A7","#81C784",
        ]
        grid = GridLayout(cols=5, spacing=dp(4), size_hint_y=None, height=dp(180))
        for c in colors:
            btn = Button(
                background_color=get_color_from_hex(c),
                size_hint=(1, None), height=dp(32)
            )
            btn.bind(on_release=lambda x, col=c: self._hover(col))
            btn.bind(on_press=lambda x, col=c: self._select(col))
            grid.add_widget(btn)
        root.add_widget(grid)

        # 自定义
        custom_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        custom_row.add_widget(Label(text="自定义:", font_size=sp(11), color=get_color_from_hex(C["text"]), size_hint=(0.2, 1)))
        self.custom_input = TextInput(
            text=self.current_color, multiline=False,
            font_size=sp(12), size_hint=(0.5, 1)
        )
        custom_row.add_widget(self.custom_input)
        ok_btn = Button(
            text="确定", font_size=sp(12),
            background_color=get_color_from_hex(C["btn_dark"]),
            color=get_color_from_hex("#ffffff"), size_hint=(0.2, 1)
        )
        ok_btn.bind(on_release=lambda x: self._select(self.custom_input.text.strip()))
        custom_row.add_widget(ok_btn)
        root.add_widget(custom_row)

        self.add_widget(root)

    def _hover(self, color):
        self.preview.background_color = get_color_from_hex(color)
        self.preview.text = color
        self.preview.color = get_color_from_hex(contrast_color(color))

    def _select(self, color):
        c = color.strip() if isinstance(color, str) else "#ffffff"
        if not c.startswith("#"):
            c = "#" + c
        if len(c) != 7:
            c = self.current_color
        self.on_select(c)
        self.dismiss()


# ============ 长按/右键菜单 ============
class ContextMenuPopup(ModalView):
    """长按弹出的操作菜单"""

    def __init__(self, item, callbacks, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.callbacks = callbacks

        self.size_hint = (0.7, None)
        self.height = dp(280)
        self.auto_dismiss = True
        self.background_color = get_color_from_hex(C["bg"]) + [0.97]

        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation="vertical", spacing=dp(4), padding=dp(8))

        root.add_widget(Label(
            text=f"  {self.item['name']}",
            font_size=sp(14), bold=True,
            color=get_color_from_hex(C["text"]),
            size_hint_y=None, height=dp(36),
            halign="left"
        ))

        # 分隔线
        sep = Widget(size_hint_y=None, height=dp(1))
        sep.bind(size=lambda s, v: setattr(s, 'height', dp(1)))
        root.add_widget(sep)

        buttons = [
            ("✏️ 修改数值", "edit_value", C["bg_alt"]),
            ("📝 修改名称", "rename", C["bg_alt"]),
            ("🎨 修改颜色", "change_color", C["bg_alt"]),
            ("🔄 切换类型(固定↔变动)", "toggle_type", C["bg_alt"]),
            ("⚙️ 设置随机选项/权重", "edit_random", C["orange"]),
            ("🗑️ 删除", "delete", C["red"]),
        ]

        for label, action, color in buttons:
            b = Button(
                text=label, font_size=sp(13),
                background_color=get_color_from_hex(color) if color != C["red"] else [0.9, 0.2, 0.2, 1],
                color=get_color_from_hex("#ffffff") if color == C["red"] else get_color_from_hex(C["text"]),
                size_hint_y=None, height=dp(36),
                halign="left"
            )
            b.bind(on_release=lambda x, a=action: self._do_action(a))
            root.add_widget(b)

        self.add_widget(root)

    def _do_action(self, action):
        self.dismiss()
        cb = self.callbacks.get(action)
        if cb:
            cb()


# ============ 主界面 ============
class SimulatorApp(App):
    title = APP_NAME

    def build(self):
        self.cfg = load_config()
        self.font_size = self.cfg.get("font_size", 14)
        self.zoom = self.cfg.get("zoom", 1.0)
        self.data = []
        self.current_file = None
        self.selected_idx = None

        self._load_data()
        self._build_ui()

        # 监听窗口尺寸变化（横竖屏切换）
        Window.bind(on_resize=self._on_resize)

        return self.root

    def _load_data(self):
        path = os.path.join(BASE_DIR, DATA_FILE)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                for d in self.data:
                    if "color" not in d: d["color"] = "#ffffff"
                    if "options" not in d and d.get("type") == "random":
                        d["options"] = []
                return
            except:
                pass
        self.data = get_default_data()

    def _save_data(self, path=None):
        if path is None:
            path = os.path.join(BASE_DIR, DATA_FILE)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self.current_file = path
            self._set_status(f"✅ 已保存: {os.path.basename(path)}")
            return True
        except Exception as e:
            self._set_status(f"❌ 保存失败: {e}")
            return False

    def _build_ui(self):
        self.root = BoxLayout(orientation="vertical", spacing=0)

        # ===== 工具栏 =====
        self.toolbar = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(50), spacing=dp(2))
        self.toolbar.bind(size=lambda s, v: setattr(s, 'height', dp(50) * self.zoom))
        self.toolbar.background_color = get_color_from_hex(C["bg_toolbar"])

        # 用 Canvas 模拟 toolbar bg
        with self.toolbar.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*get_color_from_hex(C["bg_toolbar"]))
            self._toolbar_rect = Rectangle(pos=self.toolbar.pos, size=self.toolbar.size)
        self.toolbar.bind(pos=lambda w, p: setattr(self._toolbar_rect, 'pos', p))
        self.toolbar.bind(size=lambda w, s: setattr(self._toolbar_rect, 'size', s))

        self.toolbar_btns = [
            ("💾 保存", self._on_save, C["btn_bg"]),
            ("📂 读取", self._on_load, C["btn_bg"]),
            ("➕ 固定", lambda: self._add_item("fixed"), C["btn_bg"]),
            ("➕ 变动", lambda: self._add_item("dynamic"), C["btn_bg"]),
            ("🎲 随机", lambda: self._add_item("random"), C["orange"]),
            ("🗑️ 删除", self._del_selected, C["red"]),
        ]

        for text, cmd, color in self.toolbar_btns:
            btn = Button(
                text=text, font_size=sp(12),
                background_color=get_color_from_hex(color) if color != C["red"] else [0.8, 0.2, 0.2, 1],
                color=get_color_from_hex("#ffffff") if color in [C["orange"], C["red"]] else get_color_from_hex(C["text"]),
                size_hint=(None, 0.8),
                width=dp(72) if len(text) <= 4 else dp(88),
                on_release=cmd
            )
            btn.bind(size=lambda s, v: setattr(s, 'width', dp(72) if len(s.text) <= 4 else dp(88)))
            self.toolbar.add_widget(btn)

        # 字号
        self.toolbar.add_widget(Label(text="字号", font_size=sp(10), color=get_color_from_hex(C["text_dim"]), size_hint=(None, 1), width=dp(30)))
        self.font_slider = Slider(min=10, max=22, value=self.font_size, size_hint=(None, 0.7), width=dp(60))
        self.font_slider.bind(value=self._on_font_change)
        self.toolbar.add_widget(self.font_slider)

        self.root.add_widget(self.toolbar)

        # ===== 表格区 =====
        self.table_scroll = ScrollView(size_hint=(1, 1))
        self.table_layout = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(0))
        self.table_layout.bind(minimum_height=self.table_layout.setter('height'))
        self.table_scroll.add_widget(self.table_layout)
        self.root.add_widget(self.table_scroll)

        # ===== 状态栏 =====
        self.status_bar = Label(
            text="就绪", font_size=sp(11),
            color=get_color_from_hex(C["text"]),
            size_hint=(1, None), height=dp(28),
            halign="left", valign="middle",
            padding=(dp(8), 0)
        )
        self.status_bar.bind(size=self.status_bar.setter('text_size'))
        # 状态栏背景
        with self.status_bar.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*get_color_from_hex(C["bg_dark"]))
            self._status_rect = Rectangle(pos=self.status_bar.pos, size=self.status_bar.size)
        self.status_bar.bind(pos=lambda w, p: setattr(self._status_rect, 'pos', p))
        self.status_bar.bind(size=lambda w, s: setattr(self._status_rect, 'size', s))

        self.root.add_widget(self.status_bar)

        # 渲染表格
        self._refresh_table()

    def _on_resize(self, window, width, height):
        """横竖屏切换时刷新"""
        self._refresh_table()

    def _on_font_change(self, slider, val):
        self.font_size = int(val)
        self._refresh_table()

    def _set_status(self, text):
        self.status_bar.text = text

    # ===== 表格渲染 =====
    def _refresh_table(self):
        self.table_layout.clear_widgets()

        if not self.data:
            empty = Label(
                text="（暂无属性，点击上方按钮添加）",
                font_size=sp(14), color=get_color_from_hex(C["text_dim"]),
                size_hint_y=None, height=dp(60)
            )
            self.table_layout.add_widget(empty)
            return

        w = Window.width
        # 三列比例
        col_name_w = w * 0.3
        col_type_w = w * 0.18
        col_val_w = w - col_name_w - col_type_w

        row_h = dp(40) * self.zoom

        # 表头
        header = BoxLayout(size_hint_y=None, height=row_h * 0.7, spacing=0)
        with header.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*get_color_from_hex(C["bg_dark"]))
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=lambda w, p: header.canvas.before.children[-1].set(pos=p))
        header.bind(size=lambda w, s: header.canvas.before.children[-1].set(size=s))

        header.add_widget(Label(text="属性名称", font_size=sp(self.font_size - 1), bold=True, color=get_color_from_hex(C["text"]), size_hint_x=None, width=col_name_w, halign="left", padding=(dp(8), 0)))
        header.add_widget(Label(text="类型", font_size=sp(self.font_size - 1), bold=True, color=get_color_from_hex(C["text"]), size_hint_x=None, width=col_type_w, halign="center"))
        header.add_widget(Label(text="数值", font_size=sp(self.font_size - 1), bold=True, color=get_color_from_hex(C["text"]), size_hint_x=None, width=col_val_w, halign="left", padding=(dp(8), 0)))
        self.table_layout.add_widget(header)

        # 数据行
        for i, d in enumerate(self.data):
            row = BoxLayout(size_hint_y=None, height=row_h, spacing=0)

            color = d.get("color", "#ffffff")
            text_color = contrast_color(color)
            t = d.get("type", "fixed")

            if t == "random":
                type_label = "🎲随机"
                val = str(d.get("value", "")).strip()
                if not val:
                    val = "❓ 点击抽取"
            elif t == "fixed":
                type_label = "🔒固定"
                val = str(d["value"])
            else:
                type_label = "✏️变动"
                val = str(d["value"])

            # 行背景
            with row.canvas.before:
                from kivy.graphics import Color, Rectangle
                Color(*get_color_from_hex(color))
                Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, p, r=row: setattr(r.canvas.before.children[-1], 'pos', p))
            row.bind(size=lambda w, s, r=row: setattr(r.canvas.before.children[-1], 'size', s))

            # 三列
            name_label = Label(
                text=d["name"], font_size=sp(self.font_size),
                color=get_color_from_hex(text_color),
                size_hint_x=None, width=col_name_w,
                halign="left", valign="middle",
                padding=(dp(8), 0)
            )
            name_label.bind(size=name_label.setter('text_size'))

            type_label_w = Label(
                text=type_label, font_size=sp(self.font_size - 1),
                color=get_color_from_hex(text_color),
                size_hint_x=None, width=col_type_w,
                halign="center", valign="middle"
            )
            type_label_w.bind(size=type_label_w.setter('text_size'))

            val_label = Label(
                text=val, font_size=sp(self.font_size),
                color=get_color_from_hex(text_color),
                size_hint_x=None, width=col_val_w,
                halign="left", valign="middle",
                padding=(dp(8), 0)
            )
            val_label.bind(size=val_label.setter('text_size'))

            row.add_widget(name_label)
            row.add_widget(type_label_w)
            row.add_widget(val_label)

            # 绑定事件
            row.bind(on_touch_down=lambda instance, touch, idx=i: self._on_row_touch(instance, touch, idx))

            self.table_layout.add_widget(row)

    def _on_row_touch(self, row, touch, idx):
        """处理行点击：单击数值列=编辑，长按=菜单"""
        if not row.collide_point(*touch.pos):
            return False

        # 计算点击了哪一列
        w = Window.width
        col_name_w = w * 0.3
        col_type_w = w * 0.18

        local_x = touch.x

        if touch.button == 'right' or touch.is_double_tap:
            # 右键或双击 → 菜单
            self._show_context_menu(idx, touch)
            return True

        if touch.is_mouse_scrolling:
            return False

        # 记录按下时间和位置
        touch.ud['start_time'] = time.time()
        touch.ud['start_pos'] = (touch.x, touch.y)
        touch.ud['idx'] = idx
        touch.ud['local_x'] = local_x
        touch.ud['col_name_w'] = col_name_w
        touch.ud['col_name_w_plus_type'] = col_name_w + col_type_w

        # 绑定 move 和 up
        touch.grab(row)
        row.bind(on_touch_move=lambda instance, t: self._on_row_move(instance, t, touch))
        row.bind(on_touch_up=lambda instance, t: self._on_row_up(instance, t, touch))

        return True

    def _on_row_move(self, row, touch, orig_touch):
        """检测是否超过长按阈值"""
        if 'start_time' not in orig_touch.ud:
            return False
        elapsed = time.time() - orig_touch.ud['start_time']
        if elapsed > 0.5:  # 500ms 长按
            idx = orig_touch.ud.get('idx')
            if idx is not None:
                orig_touch.ungrab(row)
                self._show_context_menu(idx, orig_touch)
            return True
        return False

    def _on_row_up(self, row, touch, orig_touch):
        """松开时判断单击操作"""
        if 'start_time' not in orig_touch.ud:
            return False

        elapsed = time.time() - orig_touch.ud['start_time']
        idx = orig_touch.ud.get('idx')
        local_x = orig_touch.ud.get('local_x', touch.x)

        try:
            orig_touch.ungrab(row)
        except:
            pass

        if elapsed > 0.5 or idx is None:
            return False

        # 判断列
        col_name_w = orig_touch.ud.get('col_name_w', Window.width * 0.3)
        col_boundary = orig_touch.ud.get('col_name_w_plus_type', Window.width * 0.48)

        if local_x < col_name_w:
            # 名称列 → 改名
            self._rename_item(idx)
        elif local_x < col_boundary:
            # 类型列 → 不处理
            pass
        else:
            # 数值列
            item = self.data[idx]
            if item.get("type") == "random" and not str(item.get("value", "")).strip():
                self._do_random_roll(idx)
            else:
                self._edit_value(idx)

        return True

    def _show_context_menu(self, idx, touch=None):
        """显示长按菜单"""
        self.selected_idx = idx
        item = self.data[idx]

        callbacks = {
            "edit_value": lambda: self._edit_value(idx),
            "rename": lambda: self._rename_item(idx),
            "change_color": lambda: self._change_color(idx),
            "toggle_type": lambda: self._toggle_type(idx),
            "edit_random": lambda: self._edit_random_options(idx),
            "delete": lambda: self._delete_item(idx),
        }

        # 如果是固定项，禁用编辑数值
        if item["type"] == "fixed":
            callbacks["edit_value"] = lambda: self._set_status(f"🔒 「{item['name']}」是固定项，请先切换为变动项")
        # 如果已锁定随机项
        if item.get("type") == "random" and str(item.get("value", "")).strip():
            callbacks["edit_value"] = lambda: self._set_status(f"🎲 「{item['name']}」已锁定，要重抽请先删除再添加")

        menu = ContextMenuPopup(item, callbacks)
        if touch:
            menu.pos = (min(touch.x - dp(100), Window.width - dp(250)),
                        min(touch.y - dp(50), Window.height - dp(300)))
        else:
            menu.pos = (Window.width // 4, Window.height // 3)
        menu.open()

    # ===== 操作函数 =====
    def _edit_value(self, idx):
        item = self.data[idx]
        if item["type"] == "fixed":
            self._set_status(f"🔒 「{item['name']}」是固定项，不可修改数值")
            return
        if item["type"] == "random":
            if not str(item.get("value", "")).strip():
                self._do_random_roll(idx)
            return

        popup = EditValuePopup(
            item["name"], item["value"],
            on_confirm=lambda new_val, i=idx: self._on_value_changed(i, new_val)
        )
        popup.open()

    def _on_value_changed(self, idx, new_val):
        old = str(self.data[idx]["value"])
        self.data[idx]["value"] = new_val
        self._set_status(f"✅ {self.data[idx]['name']}: {old} → {new_val}")
        self._refresh_table()

    def _rename_item(self, idx):
        item = self.data[idx]
        # 简单用 popup 模拟输入
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(Label(text="修改名称:", font_size=sp(12), color=get_color_from_hex(C["text"]), size_hint_y=None, height=dp(24)))
        name_in = TextInput(text=item["name"], multiline=False, font_size=sp(14), size_hint_y=None, height=dp(40))
        content.add_widget(name_in)

        btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        cancel = Button(text="取消", background_color=get_color_from_hex(C["btn_bg"]), color=get_color_from_hex(C["text"]))
        ok = Button(text="✔ 确定", background_color=get_color_from_hex(C["btn_dark"]), color=get_color_from_hex("#ffffff"))
        btn_row.add_widget(cancel)
        btn_row.add_widget(ok)
        content.add_widget(btn_row)

        popup = ModalView(size_hint=(0.8, 0.25), auto_dismiss=False)
        popup.background_color = get_color_from_hex(C["bg"]) + [1]
        popup.add_widget(content)

        def do_ok(*a):
            new_name = name_in.text.strip()
            if new_name and new_name != item["name"]:
                old = item["name"]
                self.data[idx]["name"] = new_name
                self._set_status(f"📝 {old} → {new_name}")
                self._refresh_table()
            popup.dismiss()

        ok.bind(on_release=do_ok)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _change_color(self, idx):
        item = self.data[idx]
        current = item.get("color", "#ffffff")

        def on_select(color):
            self.data[idx]["color"] = color
            self._set_status(f"🎨 {item['name']} 颜色 → {color}")
            self._refresh_table()

        picker = ColorPickerPopup(current, on_select)
        picker.open()

    def _toggle_type(self, idx):
        t = self.data[idx]["type"]
        if t == "random":
            self.data[idx]["type"] = "fixed"
            if not self.data[idx].get("value"):
                self.data[idx]["value"] = ""
        elif t == "fixed":
            self.data[idx]["type"] = "dynamic"
        else:
            self.data[idx]["type"] = "fixed"
        label = {"fixed":"固定","dynamic":"变动","random":"随机"}[self.data[idx]["type"]]
        self._set_status(f"🔄 → {label}")
        self._refresh_table()

    def _delete_item(self, idx):
        name = self.data[idx]["name"]
        # 确认
        content = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        content.add_widget(Label(text=f"确定删除「{name}」？", font_size=sp(13), color=get_color_from_hex(C["text"])))
        btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        cancel = Button(text="取消", background_color=get_color_from_hex(C["btn_bg"]), color=get_color_from_hex(C["text"]))
        ok = Button(text="✔ 删除", background_color=[0.8, 0.2, 0.2, 1], color=get_color_from_hex("#ffffff"))
        btn_row.add_widget(cancel)
        btn_row.add_widget(ok)
        content.add_widget(btn_row)

        popup = ModalView(size_hint=(0.7, 0.2), auto_dismiss=False)
        popup.background_color = get_color_from_hex(C["bg"]) + [1]
        popup.add_widget(content)

        def do_del(*a):
            del self.data[idx]
            self._set_status(f"🗑️ 已删除: {name}")
            self._refresh_table()
            popup.dismiss()

        ok.bind(on_release=do_del)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _edit_random_options(self, idx):
        item = self.data[idx]
        cur_opts = list(item.get("options", []))

        def on_save(new_opts):
            self.data[idx]["options"] = list(new_opts)
            if self.data[idx].get("type") != "random":
                self.data[idx]["type"] = "random"
                self.data[idx]["value"] = ""
            self._set_status(f"⚙️ {item['name']} 的随机选项已更新")
            self._refresh_table()

        popup = EditRandomOptionsPopup(item["name"], cur_opts, on_save)
        popup.open()

    def _do_random_roll(self, idx):
        item = self.data[idx]
        options = item.get("options", [])
        if not options:
            self._set_status(f"⚠️ 「{item['name']}」没有随机选项，请先设置")
            return

        def on_result(result):
            if not result:
                return
            self.data[idx]["value"] = result
            self.data[idx]["type"] = "fixed"
            self._set_status(f"🎲 {item['name']}: → {result}（已锁定）")
            self._refresh_table()

        popup = RollPopup(item["name"], options, on_result)
        popup.open()

    # ===== 添加属性 =====
    def _add_item(self, default_type):
        def on_confirm(result):
            self.data.append(result)
            label = {"fixed":"固定","dynamic":"变动","random":"随机"}.get(result.get("type"), "?")
            self._set_status(f"➕ {result['name']} ({label})")
            self._refresh_table()

        popup = AddItemPopup(on_confirm, default_type=default_type)
        popup.open()

    # ===== 保存/读取 =====
    def _on_save(self, *args):
        if self.current_file:
            self._save_data(self.current_file)
        else:
            self._on_save_as()

    def _on_save_as(self, *args):
        # Android 上文件选择比较特殊，这里用简单的命名
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(12))
        content.add_widget(Label(text="输入存档文件名:", font_size=sp(12), color=get_color_from_hex(C["text"]), size_hint_y=None, height=dp(24)))
        name_in = TextInput(text="存档.json", multiline=False, font_size=sp(13), size_hint_y=None, height=dp(36))
        content.add_widget(name_in)

        btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        cancel = Button(text="取消", background_color=get_color_from_hex(C["btn_bg"]), color=get_color_from_hex(C["text"]))
        ok = Button(text="✔ 保存", background_color=get_color_from_hex(C["btn_dark"]), color=get_color_from_hex("#ffffff"))
        btn_row.add_widget(cancel)
        btn_row.add_widget(ok)
        content.add_widget(btn_row)

        popup = ModalView(size_hint=(0.8, 0.25), auto_dismiss=False)
        popup.background_color = get_color_from_hex(C["bg"]) + [1]
        popup.add_widget(content)

        def do_save(*a):
            fname = name_in.text.strip() or "存档.json"
            if not fname.endswith(".json"):
                fname += ".json"
            path = os.path.join(SAVE_FOLDER, fname)
            if self._save_data(path):
                popup.dismiss()

        ok.bind(on_release=do_save)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _on_load(self, *args):
        """简易存档列表选择"""
        folder = SAVE_FOLDER
        try:
            files = [f for f in os.listdir(folder) if f.endswith(".json")]
        except:
            files = []

        # 也加入根目录的 data.json
        root_data = os.path.join(BASE_DIR, DATA_FILE)
        if os.path.exists(root_data) and DATA_FILE not in files:
            files.insert(0, DATA_FILE)

        if not files:
            self._set_status("📂 没有找到存档文件")
            return

        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(12))
        content.add_widget(Label(text="选择存档文件:", font_size=sp(13), bold=True, color=get_color_from_hex(C["text"]), size_hint_y=None, height=dp(28)))

        scroll = ScrollView(size_hint=(1, 1))
        file_list = BoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None)
        file_list.bind(minimum_height=file_list.setter('height'))

        for f in files:
            row = BoxLayout(size_hint_y=None, height=dp(36))
            b = Button(
                text=f"📄 {f}",
                font_size=sp(12),
                background_color=get_color_from_hex(C["bg_alt"]),
                color=get_color_from_hex(C["text"]),
                halign="left"
            )
            path = os.path.join(folder, f) if f != DATA_FILE else root_data
            b.bind(on_release=lambda x, p=path: self._load_from_path(p, popup))
            row.add_widget(b)
            file_list.add_widget(row)

        scroll.add_widget(file_list)
        content.add_widget(scroll)

        popup = ModalView(size_hint=(0.85, 0.6), auto_dismiss=True)
        popup.background_color = get_color_from_hex(C["bg"]) + [1]
        popup.add_widget(content)
        popup.open()

    def _load_from_path(self, path, popup):
        try:
            with open(path, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            if isinstance(new_data, list):
                for d in new_data:
                    if "color" not in d: d["color"] = "#ffffff"
                    if "options" not in d and d.get("type") == "random":
                        d["options"] = []
                self.data = new_data
                self.current_file = path
                self._set_status(f"📂 已读取: {os.path.basename(path)}")
                self._refresh_table()
                popup.dismiss()
        except Exception as e:
            self._set_status(f"❌ 读取失败: {e}")

    # ===== 删除选中 =====
    def _del_selected(self, *args):
        if self.selected_idx is not None and self.selected_idx < len(self.data):
            self._delete_item(self.selected_idx)
        else:
            self._set_status("请先长按选中要删除的行")

    # ===== 应用暂停时自动保存 =====
    def on_pause(self):
        self._save_data()
        cfg = {"font_size": self.font_size, "zoom": self.zoom}
        save_config(cfg)
        return True

    def on_stop(self):
        self._save_data()
        cfg = {"font_size": self.font_size, "zoom": self.zoom}
        save_config(cfg)


# ============ 入口 ============
if __name__ == "__main__":
    SimulatorApp().run()
