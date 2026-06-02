"""Hermes 人格配置管理模块

支持多个人格切换，每个人格对应独立的 Hermes API/Profile。
配置存储在 personas.json 中，支持运行时添加/编辑/删除。
"""

import json
import os
import logging
from typing import Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSONAS_FILE = os.path.join(CONFIG_DIR, "personas.json")


@dataclass
class Persona:
    """人格配置"""
    id: str                    # 唯一标识（英文，用于文件名等）
    name: str                  # 显示名称（中文）
    api_endpoint: str          # Hermes API 地址
    api_key: str               # API 密钥
    model_name: str            # Model 名称（对应 profile 名）
    skin: str                  # 形象图片文件名
    system_prompt: str = ""    # 客户端补充的 system prompt
    theme_color: str = "#B088C0"  # 主题色
    description: str = ""      # 人格描述
    greetings: list = None     # 问候语列表
    # 语音配置
    tts_provider: str = ""     # TTS 提供商（edge-tts, xiaomi, openai），空则用全局配置
    tts_model: str = ""        # TTS 模型名称（如 tts-1），空则用全局配置
    tts_voice: str = ""        # 音色名称，空则用全局配置
    tts_api_key: str = ""      # TTS API Key（可选，覆盖全局）
    tts_endpoint: str = ""     # TTS API 端点（可选，覆盖全局）
    
    def __post_init__(self):
        if self.greetings is None:
            self.greetings = self._default_greetings()
    
    def _default_greetings(self):
        """根据人格类型返回默认问候语"""
        defaults = {
            "小赫": [
                "主人好呀～(◕ᴗ◕✿)",
                "嘿嘿，主人来了！✧(≖ ◡ ≖✿)",
                "想小赫了吗～♪(´ε` )",
                "主人今天也要加油哦！(ง •̀_•́)ง",
            ],
        }
        return defaults.get(self.name, [f"你好，我是{self.name}，有什么可以帮你的？"])


class PersonaManager:
    """人格管理器"""
    
    def __init__(self):
        self.personas: dict[str, Persona] = {}
        self.current_id: Optional[str] = None
        self._load()
    
    def _load(self):
        """从配置文件加载人格列表"""
        if not os.path.exists(PERSONAS_FILE):
            # 创建默认配置
            self._create_default()
            return
        
        try:
            with open(PERSONAS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for p_data in data.get("personas", []):
                persona = Persona(**p_data)
                self.personas[persona.id] = persona
            
            # 加载上次使用的人格
            self.current_id = data.get("current_id")
            if self.current_id and self.current_id not in self.personas:
                self.current_id = None
            
            logger.info(f"加载了 {len(self.personas)} 个人格配置")
            
        except Exception as e:
            logger.error(f"加载人格配置失败: {e}")
            self._create_default()
    
    def _create_default(self):
        """创建默认配置（小赫）"""
        default = Persona(
            id="xiaohe",
            name="小赫",
            api_endpoint="http://localhost:8643/v1/chat/completions",
            api_key="desktop-pet-key-2026",
            model_name="desktop-pet",
            skin="angel_sprite.png",
            system_prompt="你是一个住在用户桌面的宠物精灵。对话在桌面气泡中显示，所以回复要简短。不要使用 Markdown 格式，用纯文本。",
            theme_color="#B088C0",
            description="可爱的桌面宠物精灵",
            greetings=[
                "主人好呀～(◕ᴗ◕✿)",
                "嘿嘿，主人来了！✧(≖ ◡ ≖✿)",
                "想小赫了吗～♪(´ε` )",
                "主人今天也要加油哦！(ง •̀_•́)ง",
                "小赫一直在等你呢 (´;ω;`)",
                "诶嘿～有什么需要帮忙的吗？",
            ]
        )
        self.personas[default.id] = default
        self.current_id = default.id
        self._save()
    
    def _save(self):
        """保存配置到文件"""
        data = {
            "current_id": self.current_id,
            "personas": [asdict(p) for p in self.personas.values()]
        }
        
        try:
            with open(PERSONAS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"保存人格配置: {len(self.personas)} 个人格")
        except Exception as e:
            logger.error(f"保存人格配置失败: {e}")
    
    def get_current(self) -> Optional[Persona]:
        """获取当前人格"""
        if self.current_id and self.current_id in self.personas:
            return self.personas[self.current_id]
        # 如果没有当前人格，返回第一个
        if self.personas:
            return next(iter(self.personas.values()))
        return None
    
    def get_all(self) -> list[Persona]:
        """获取所有人格"""
        return list(self.personas.values())
    
    def switch_to(self, persona_id: str) -> bool:
        """切换到指定人格"""
        if persona_id not in self.personas:
            logger.error(f"人格不存在: {persona_id}")
            return False
        
        self.current_id = persona_id
        self._save()
        logger.info(f"切换到人格: {self.personas[persona_id].name}")
        return True
    
    def add(self, persona: Persona) -> bool:
        """添加新人格"""
        if persona.id in self.personas:
            logger.error(f"人格ID已存在: {persona.id}")
            return False
        
        self.personas[persona.id] = persona
        self._save()
        logger.info(f"添加人格: {persona.name}")
        return True
    
    def update(self, persona: Persona) -> bool:
        """更新人格配置"""
        if persona.id not in self.personas:
            logger.error(f"人格不存在: {persona.id}")
            return False
        
        self.personas[persona.id] = persona
        self._save()
        logger.info(f"更新人格: {persona.name}")
        return True
    
    def delete(self, persona_id: str) -> bool:
        """删除人格"""
        if persona_id not in self.personas:
            logger.error(f"人格不存在: {persona_id}")
            return False
        
        # 不能删除当前人格
        if persona_id == self.current_id:
            logger.error("不能删除当前使用的人格")
            return False
        
        del self.personas[persona_id]
        self._save()
        logger.info(f"删除人格: {persona_id}")
        return True


# 全局单例
persona_manager = PersonaManager()
