"""主题管理模块 — 定义和切换应用主题"""

from dataclasses import dataclass
from typing import Dict, Optional
import json
import os


@dataclass
class Theme:
    """主题配色方案"""
    id: str
    name: str
    
    # 聊天气泡配色
    bubble_bg: str = "rgba(255, 255, 255, 230)"
    bubble_border: str = "#E0D0F0"
    user_msg: str = "#E8DEF8"
    hermes_msg: str = "#F0E6FF"
    input_bg: str = "#FFFFFF"
    input_border: str = "#D0C0E0"
    send_btn: str = "#B088C0"
    send_btn_hover: str = "#9868A8"
    text: str = "#2D2D2D"
    text_secondary: str = "#666666"
    
    # 强调色（用于高亮、选中等）
    accent: str = "#B088C0"
    accent_light: str = "#E8DEF8"


# 预设主题
THEMES: Dict[str, Theme] = {
    "purple": Theme(
        id="purple",
        name="💜 梦幻紫",
        bubble_bg="rgba(255, 255, 255, 230)",
        bubble_border="#E0D0F0",
        user_msg="#E8DEF8",
        hermes_msg="#F0E6FF",
        input_bg="#FFFFFF",
        input_border="#D0C0E0",
        send_btn="#B088C0",
        send_btn_hover="#9868A8",
        text="#2D2D2D",
        text_secondary="#666666",
        accent="#B088C0",
        accent_light="#E8DEF8",
    ),
    "pink": Theme(
        id="pink",
        name="🌸 樱花粉",
        bubble_bg="rgba(255, 255, 255, 230)",
        bubble_border="#FFD0D8",
        user_msg="#FFE0E8",
        hermes_msg="#FFF0F4",
        input_bg="#FFFFFF",
        input_border="#FFD0D8",
        send_btn="#FF8DA1",
        send_btn_hover="#FF6B85",
        text="#2D2D2D",
        text_secondary="#886666",
        accent="#FF8DA1",
        accent_light="#FFE0E8",
    ),
    "blue": Theme(
        id="blue",
        name="🌊 清澈蓝",
        bubble_bg="rgba(255, 255, 255, 230)",
        bubble_border="#C0D8F0",
        user_msg="#D8E8FF",
        hermes_msg="#E8F0FF",
        input_bg="#FFFFFF",
        input_border="#C0D8F0",
        send_btn="#6B9FE8",
        send_btn_hover="#5080C0",
        text="#2D2D2D",
        text_secondary="#666688",
        accent="#6B9FE8",
        accent_light="#D8E8FF",
    ),
    "green": Theme(
        id="green",
        name="🌿 清新绿",
        bubble_bg="rgba(255, 255, 255, 230)",
        bubble_border="#C0E0C8",
        user_msg="#D8F0DC",
        hermes_msg="#E8F8EC",
        input_bg="#FFFFFF",
        input_border="#C0E0C8",
        send_btn="#6BC080",
        send_btn_hover="#50A060",
        text="#2D2D2D",
        text_secondary="#668866",
        accent="#6BC080",
        accent_light="#D8F0DC",
    ),
    "orange": Theme(
        id="orange",
        name="🍊 暖阳橙",
        bubble_bg="rgba(255, 255, 255, 230)",
        bubble_border="#F0D0B0",
        user_msg="#FFE8D0",
        hermes_msg="#FFF4E8",
        input_bg="#FFFFFF",
        input_border="#F0D0B0",
        send_btn="#F0A060",
        send_btn_hover="#E08040",
        text="#2D2D2D",
        text_secondary="#886644",
        accent="#F0A060",
        accent_light="#FFE8D0",
    ),
    "dark": Theme(
        id="dark",
        name="🌙 暗夜黑",
        bubble_bg="rgba(40, 40, 50, 240)",
        bubble_border="#404050",
        user_msg="#3A3A50",
        hermes_msg="#2A2A40",
        input_bg="#2A2A38",
        input_border="#404050",
        send_btn="#6B6B8D",
        send_btn_hover="#505070",
        text="#E0E0E0",
        text_secondary="#9090A0",
        accent="#6B6B8D",
        accent_light="#3A3A50",
    ),
}

# 当前主题
_current_theme_id: str = "purple"
_theme_change_callbacks: list = []


def get_current_theme() -> Theme:
    """获取当前主题"""
    return THEMES.get(_current_theme_id, THEMES["purple"])


def get_all_themes() -> list:
    """获取所有可用主题"""
    return list(THEMES.values())


def set_theme(theme_id: str) -> bool:
    """切换主题，返回是否成功"""
    global _current_theme_id
    if theme_id not in THEMES:
        return False
    
    _current_theme_id = theme_id
    _save_preference(theme_id)
    
    # 通知所有监听者
    for callback in _theme_change_callbacks:
        try:
            callback(THEMES[theme_id])
        except Exception:
            pass
    
    return True


def on_theme_change(callback):
    """注册主题变更回调"""
    _theme_change_callbacks.append(callback)


def _save_preference(theme_id: str):
    """保存主题偏好到文件"""
    prefs_path = _get_prefs_path()
    try:
        prefs = {}
        if os.path.exists(prefs_path):
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        prefs["theme"] = theme_id
        with open(prefs_path, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_preference():
    """加载主题偏好"""
    global _current_theme_id
    prefs_path = _get_prefs_path()
    try:
        if os.path.exists(prefs_path):
            with open(prefs_path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
            theme_id = prefs.get("theme", "purple")
            if theme_id in THEMES:
                _current_theme_id = theme_id
    except Exception:
        pass


def _get_prefs_path() -> str:
    """获取偏好文件路径"""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "user_prefs.json"
    )


# 启动时加载偏好
load_preference()
