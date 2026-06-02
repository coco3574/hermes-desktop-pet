"""Hermes Desktop Pet 配置模块

所有配置项均支持环境变量覆盖，也可直接修改下方默认值。
"""

import os
from pathlib import Path

# 加载 .env 文件
def _load_dotenv():
    """从项目根目录加载 .env 文件"""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value

_load_dotenv()

# === API 配置 ===
# Hermes API Server 地址（需要先启动 Hermes Gateway）
API_ENDPOINT: str = os.environ.get(
    "HERMES_API_ENDPOINT", "http://localhost:8643/v1/chat/completions"
)
# API 密钥（与 Hermes Gateway 配置一致）
API_KEY: str = os.environ.get("HERMES_DESKTOP_PET_KEY", "desktop-pet-key-2026")
# 模型名称（对应 Hermes profile 名称）
MODEL_NAME: str = os.environ.get("HERMES_MODEL_NAME", "desktop-pet")

# === 系统提示词 ===
# 注：人格由 profile 的 SOUL.md 定义，这里只需补充应用层上下文
SYSTEM_PROMPT: str = (
    "你是一个住在用户桌面的宠物精灵。对话在桌面气泡中显示，所以回复要简短。"
    "不要使用 Markdown 格式，用纯文本。"
)

# === 窗口配置 ===
PET_WIDTH: int = int(os.environ.get("PET_WIDTH", "150"))
PET_HEIGHT: int = int(os.environ.get("PET_HEIGHT", "200"))
CHAT_WIDTH: int = int(os.environ.get("CHAT_WIDTH", "360"))
CHAT_HEIGHT: int = int(os.environ.get("CHAT_HEIGHT", "480"))

# === 颜色配置 ===
# 角色配色（柔和粉紫系）
COLOR_HAIR: str = "#8B6FAE"
COLOR_HAIR_HIGHLIGHT: str = "#A78BBF"
COLOR_SKIN: str = "#FDDCB5"
COLOR_EYE: str = "#6B4E8D"
COLOR_EYE_SHINE: str = "#FFFFFF"
COLOR_CHEEK: str = "#FFB6C1"
COLOR_DRESS: str = "#D8A0D0"
COLOR_DRESS_DETAIL: str = "#C080B8"
COLOR_RIBBON: str = "#FF8C94"
COLOR_SHOES: str = "#8B6FAE"

# 聊天气泡配色
COLOR_BUBBLE_BG: str = "rgba(255, 255, 255, 230)"
COLOR_BUBBLE_BORDER: str = "#E0D0F0"
COLOR_USER_MSG: str = "#E8DEF8"
COLOR_HERMES_MSG: str = "#F0E6FF"
COLOR_INPUT_BG: str = "#FFFFFF"
COLOR_INPUT_BORDER: str = "#D0C0E0"
COLOR_SEND_BTN: str = "#B088C0"
COLOR_SEND_BTN_HOVER: str = "#9868A8"
COLOR_TEXT: str = "#2D2D2D"
COLOR_TEXT_SECONDARY: str = "#666666"

# === 字体配置 ===
FONT_FAMILY: str = os.environ.get("FONT_FAMILY", "Microsoft YaHei, Segoe UI, Arial")
FONT_SIZE_CHAT: int = int(os.environ.get("FONT_SIZE_CHAT", "13"))
FONT_SIZE_INPUT: int = int(os.environ.get("FONT_SIZE_INPUT", "13"))
FONT_SIZE_LABEL: int = int(os.environ.get("FONT_SIZE_LABEL", "11"))

# === API 请求配置 ===
API_TIMEOUT: float = float(os.environ.get("API_TIMEOUT", "120.0"))
MAX_HISTORY_LENGTH: int = int(os.environ.get("MAX_HISTORY_LENGTH", "50"))

# === 语音配置 ===
# TTS 提供商: "edge-tts" | "xiaomi" | "openai"
TTS_PROVIDER: str = os.environ.get("TTS_PROVIDER", "xiaomi")
TTS_MODEL: str = os.environ.get("TTS_MODEL", "")  # TTS 模型名称（xiaomi/openai 用）
TTS_VOICE: str = os.environ.get("TTS_VOICE", "Chloe")

# STT 提供商: "google" | "xiaomi" | "openai"
STT_PROVIDER: str = os.environ.get("STT_PROVIDER", "google")

# 小米语音 API
XIAOMI_API_KEY: str = os.environ.get("XIAOMI_API_KEY", os.environ.get("MIMO_API_KEY", ""))
XIAOMI_BASE_URL: str = os.environ.get("XIAOMI_BASE_URL", "https://api.xiaomimimo.com/v1")
XIAOMI_TTS_MODEL: str = os.environ.get("XIAOMI_TTS_MODEL", "mimo-v2.5-tts")
XIAOMI_TTS_VOICE: str = os.environ.get("XIAOMI_TTS_VOICE", "Chloe")
XIAOMI_STT_ENDPOINT: str = "https://api.xiaomimimo.com/v1/audio/transcriptions"
XIAOMI_STT_MODEL: str = "whisper-1"

# OpenAI 语音 API
OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
