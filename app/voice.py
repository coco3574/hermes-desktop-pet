"""语音模块 — 可配置的 TTS/STT 提供商

支持的 TTS 提供商:
  - edge-tts    : 微软免费语音（默认）
  - xiaomi      : 小米语音模型
  - openai      : OpenAI TTS

支持的 STT 提供商:
  - google      : Google 免费语音识别（默认）
  - xiaomi      : 小米语音识别
  - openai      : OpenAI Whisper

修改 config.py 中的 TTS_PROVIDER / STT_PROVIDER 即可切换。
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)

AUDIO_CACHE = Path(tempfile.gettempdir()) / "hermes_desktop_pet_audio"
AUDIO_CACHE.mkdir(exist_ok=True)


# ════════════════════════════════════════
#  TTS — 文字转语音
# ════════════════════════════════════════

class TTSSpeaker(QThread):
    """后台线程：将文字转为语音并播放。"""

    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, text: str, provider: str = None, model: str = None,
                 voice: str = None, api_key: str = None, endpoint: str = None, parent=None):
        super().__init__(parent)
        self.text = text
        # 延迟导入 config，避免循环引用
        from . import config
        from .personas import persona_manager

        # 获取当前人格的语音配置
        current_persona = persona_manager.get_current()

        # 优先级：参数 > 人格配置 > 全局配置
        if provider:
            self.provider = provider
        elif current_persona and current_persona.tts_provider:
            self.provider = current_persona.tts_provider
        else:
            self.provider = config.TTS_PROVIDER

        # TTS 模型名称（xiaomi/openai 用）
        if model:
            self.model = model
        elif current_persona and current_persona.tts_model:
            self.model = current_persona.tts_model
        else:
            self.model = config.TTS_MODEL

        if voice:
            self.voice = voice
        elif current_persona and current_persona.tts_voice:
            self.voice = current_persona.tts_voice
        else:
            self.voice = config.TTS_VOICE

        # API Key 和端点（用于 xiaomi 和 openai）
        if api_key:
            self.api_key = api_key
        elif current_persona and current_persona.tts_api_key:
            self.api_key = current_persona.tts_api_key
        else:
            # 根据 provider 选择默认 API Key
            if self.provider == "xiaomi":
                self.api_key = config.XIAOMI_API_KEY
            elif self.provider == "openai":
                self.api_key = config.OPENAI_API_KEY
            else:
                self.api_key = ""

        if endpoint:
            self.endpoint = endpoint
        elif current_persona and current_persona.tts_endpoint:
            self.endpoint = current_persona.tts_endpoint
        else:
            # 根据 provider 选择默认端点
            if self.provider == "xiaomi":
                self.endpoint = config.XIAOMI_BASE_URL
            elif self.provider == "openai":
                self.endpoint = "https://api.openai.com/v1/audio/speech"
            else:
                self.endpoint = ""

    def run(self):
        try:
            # 根据 provider 选择文件格式
            if self.provider == "xiaomi":
                audio_path = AUDIO_CACHE / "reply.wav"
            else:
                audio_path = AUDIO_CACHE / "reply.mp3"

            if self.provider == "edge-tts":
                self._generate_edge_tts(audio_path)
            elif self.provider == "xiaomi":
                self._generate_xiaomi_tts(audio_path)
            elif self.provider == "openai":
                self._generate_openai_tts(audio_path)
            else:
                self.error.emit(f"未知的 TTS 提供商: {self.provider}")
                return

            self._play_audio(audio_path)

        except Exception as e:
            logger.exception("TTS 播放失败")
            self.error.emit(f"语音播放失败: {e}")
        finally:
            self.finished.emit()

    def _generate_edge_tts(self, path: Path):
        """微软 edge-tts（免费）。"""
        import edge_tts

        async def _gen():
            communicate = edge_tts.Communicate(self.text, self.voice)
            await communicate.save(str(path))

        asyncio.run(_gen())

    def _generate_xiaomi_tts(self, path: Path):
        """小米 TTS — 通过 chat.completions 接口调用。"""
        import httpx
        import base64

        # 小米 TTS 格式：user 是风格描述，assistant 是要朗读的内容
        style_prompt = "请用自然、亲切的语气朗读。"
        
        resp = httpx.post(
            f"{self.endpoint}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model or "mimo-v2.5-tts",
                "messages": [
                    {"role": "user", "content": style_prompt},
                    {"role": "assistant", "content": self.text}
                ],
                "audio": {
                    "format": "wav",
                    "voice": self.voice or "Chloe"
                }
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        
        # 解析音频数据
        audio_data = data["choices"][0]["message"]["audio"]["data"]
        audio_bytes = base64.b64decode(audio_data)
        path.write_bytes(audio_bytes)

    def _generate_openai_tts(self, path: Path):
        """OpenAI TTS。"""
        import httpx

        resp = httpx.post(
            self.endpoint,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model or "tts-1",
                "input": self.text,
                "voice": self.voice or "alloy",
            },
            timeout=30,
        )
        resp.raise_for_status()
        path.write_bytes(resp.content)

    def _play_audio(self, path: Path):
        """播放音频文件。"""
        logger.info("TTS: 播放音频 %s", path)
        if os.name == "nt":
            # 使用 PowerShell 后台播放，无弹窗
            logger.info("TTS: 后台播放...")
            win_path = str(path).replace("/", "\\")
            ps_script = f'''
            Add-Type -AssemblyName presentationCore
            $player = New-Object System.Windows.Media.MediaPlayer
            $player.Open([System.Uri]::new("{win_path}"))
            $player.Play()
            Start-Sleep -Milliseconds 500
            while ($player.Position -lt $player.NaturalDuration.TimeSpan) {{
                Start-Sleep -Milliseconds 100
            }}
            $player.Close()
            '''
            
            # 保存到临时 ps1 文件
            ps_file = path.parent / "play.ps1"
            ps_file.write_text(ps_script, encoding="utf-8")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
            subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(ps_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            logger.info("TTS: 播放进程已启动")
        else:
            for player in ["mpv", "ffplay", "aplay"]:
                try:
                    subprocess.run([player, str(path)], capture_output=True, timeout=60)
                    break
                except FileNotFoundError:
                    continue


# ════════════════════════════════════════
#  STT — 语音转文字
# ════════════════════════════════════════

class STTListener(QThread):
    """后台线程：麦克风录音并转为文字。"""

    result = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, provider: str = None, parent=None):
        super().__init__(parent)
        self._abort = False
        from . import config
        self.provider = provider or config.STT_PROVIDER

    def abort(self):
        self._abort = True

    def run(self):
        try:
            audio_data = self._record_audio()
            if self._abort or not audio_data:
                return

            if self.provider == "google":
                text = self._recognize_google(audio_data)
            elif self.provider == "xiaomi":
                text = self._recognize_xiaomi(audio_data)
            elif self.provider == "openai":
                text = self._recognize_openai(audio_data)
            else:
                self.error.emit(f"未知的 STT 提供商: {self.provider}")
                return

            if text:
                logger.info("识别结果: %s", text)
                self.result.emit(text)

        except Exception as e:
            logger.exception("STT 识别失败")
            if "timeout" in str(e).lower() or "listening" in str(e).lower():
                self.error.emit("没有检测到语音，请再试一次")
            else:
                self.error.emit(f"语音识别失败: {e}")
        finally:
            self.finished.emit()

    def _record_audio(self):
        """录音并返回音频数据。"""
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            logger.info("正在调整环境噪音...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.info("请说话...")
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=30)
        return audio

    def _recognize_google(self, audio) -> str:
        """Google 免费语音识别。"""
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        return recognizer.recognize_google(audio, language="zh-CN")

    def _recognize_xiaomi(self, audio) -> str:
        """小米语音识别 — 通过 OpenAI Whisper 兼容接口。"""
        import httpx
        from . import config

        # 将 audio 数据转为 WAV
        wav_data = audio.get_wav_data()

        resp = httpx.post(
            config.XIAOMI_STT_ENDPOINT,
            headers={"Authorization": f"Bearer {config.XIAOMI_API_KEY}"},
            files={"file": ("audio.wav", wav_data, "audio/wav")},
            data={"model": config.XIAOMI_STT_MODEL, "language": "zh"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("text", "")

    def _recognize_openai(self, audio) -> str:
        """OpenAI Whisper 语音识别。"""
        import httpx
        from . import config

        wav_data = audio.get_wav_data()

        resp = httpx.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            files={"file": ("audio.wav", wav_data, "audio/wav")},
            data={"model": "whisper-1", "language": "zh"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("text", "")
