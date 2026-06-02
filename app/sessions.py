"""会话管理模块 — 保存和加载聊天会话"""

import json
import os
import time
from typing import Optional
from dataclasses import dataclass, asdict

# 会话存储目录
SESSIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sessions"
)


@dataclass
class Session:
    """会话数据"""
    id: str              # 唯一标识（时间戳）
    name: str            # 会话名称（取自第一条用户消息）
    persona_id: str      # 关联的人格 ID
    messages: list       # 消息历史
    created_at: float    # 创建时间
    updated_at: float    # 更新时间


class SessionManager:
    """会话管理器"""
    
    def __init__(self):
        self._current_session: Optional[Session] = None
        self._ensure_dir()
    
    def _ensure_dir(self):
        """确保存在会话目录"""
        if not os.path.exists(SESSIONS_DIR):
            os.makedirs(SESSIONS_DIR)
    
    def _get_session_path(self, session_id: str) -> str:
        """获取会话文件路径"""
        return os.path.join(SESSIONS_DIR, f"{session_id}.json")
    
    def create_session(self, persona_id: str, messages: list) -> Session:
        """创建新会话"""
        session_id = str(int(time.time() * 1000))
        now = time.time()
        
        # 从消息中提取名称
        name = "新会话"
        for msg in messages:
            if msg.get("role") == "user":
                name = msg.get("content", "")[:30]
                break
        
        session = Session(
            id=session_id,
            name=name,
            persona_id=persona_id,
            messages=messages,
            created_at=now,
            updated_at=now
        )
        
        self._save_session(session)
        self._current_session = session
        return session
    
    def save_current(self, messages: list):
        """保存当前会话"""
        if not self._current_session:
            return
        
        # 更新消息和时间
        self._current_session.messages = messages
        self._current_session.updated_at = time.time()
        
        # 更新名称（如果还没有用户消息）
        if self._current_session.name == "新会话":
            for msg in messages:
                if msg.get("role") == "user":
                    self._current_session.name = msg.get("content", "")[:30]
                    break
        
        self._save_session(self._current_session)
    
    def load_session(self, session_id: str) -> Optional[Session]:
        """加载指定会话"""
        path = self._get_session_path(session_id)
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            session = Session(**data)
            self._current_session = session
            return session
        except Exception:
            return None
    
    def get_all_sessions(self) -> list[Session]:
        """获取所有会话列表"""
        sessions = []
        self._ensure_dir()
        
        for filename in os.listdir(SESSIONS_DIR):
            if filename.endswith(".json"):
                session_id = filename[:-5]
                session = self._load_session_file(session_id)
                if session:
                    sessions.append(session)
        
        # 按更新时间倒序排列
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions
    
    def _load_session_file(self, session_id: str) -> Optional[Session]:
        """从文件加载会话"""
        path = self._get_session_path(session_id)
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Session(**data)
        except Exception:
            return None
    
    def _save_session(self, session: Session):
        """保存会话到文件"""
        path = self._get_session_path(session.id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(asdict(session), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Session] 保存会话失败: {e}")
    
    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        path = self._get_session_path(session_id)
        if os.path.exists(path):
            try:
                os.remove(path)
                if self._current_session and self._current_session.id == session_id:
                    self._current_session = None
                return True
            except Exception:
                return False
        return False
    
    def get_current(self) -> Optional[Session]:
        """获取当前会话"""
        return self._current_session
    
    def clear_current(self):
        """清除当前会话"""
        self._current_session = None


# 全局单例
session_manager = SessionManager()
