"""Hermes Desktop Pet — 桌面宠物聊天应用入口"""

import os
import sys
import logging

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from app.config import FONT_FAMILY
from app.pet_window import PetWindow
from app.chat_bubble import ChatBubble
from app.tray_icon import TrayIcon
from app.api_client import ChatManager
from app.voice import TTSSpeaker, STTListener
from app.personas import persona_manager

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_global_style(app: QApplication):
    """设置全局样式。"""
    app.setStyleSheet(f"""
        * {{
            font-family: {FONT_FAMILY};
        }}
    """)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口不退出，靠托盘维持
    setup_global_style(app)

    # 创建核心组件
    pet = PetWindow()
    chat = ChatBubble()
    tray = TrayIcon()
    chat_mgr = ChatManager()

    # ── 人格切换处理 ──
    
    def on_persona_changed(persona_id: str):
        """人格切换回调"""
        logger.info(f"切换人格: {persona_id}")
        
        # 更新聊天管理器的 system prompt
        chat_mgr.switch_persona()
        
        # 更新窗口标题
        current = persona_manager.get_current()
        if current:
            chat.setWindowTitle(f"Hermes - {current.name}")
        
        # 清空聊天显示
        chat.clear_messages()
        
        logger.info(f"人格切换完成: {current.name if current else '未知'}")
    
    pet.persona_changed.connect(on_persona_changed)

    # ── 位置追踪：聊天窗口跟随宠物移动 ──

    class PosTracker:
        def __init__(self):
            self._last_pos = None

        def check(self):
            if pet.pos() != self._last_pos:
                self._last_pos = pet.pos()
                if chat.isVisible():
                    chat.move(pet.pos().x() - chat.width() - 10, pet.pos().y())

    tracker = PosTracker()
    pos_timer = QTimer()
    pos_timer.timeout.connect(tracker.check)
    pos_timer.setInterval(50)

    # ── 宠物点击 → 切换聊天窗口 ──

    def on_pet_click():
        chat.toggle_visibility()

    def on_hide_all():
        pet.hide()
        chat.hide()

    pet._on_click = on_pet_click
    pet._toggle_chat = on_pet_click
    pet._hide_all = on_hide_all

    # ── 聊天窗口 toggle 时启动/停止位置追踪 ──

    original_toggle = chat.toggle_visibility

    def tracked_toggle():
        original_toggle()
        if chat.isVisible():
            # 立即同步位置
            chat.move(pet.pos().x() - chat.width() - 10, pet.pos().y())
            pos_timer.start()
        else:
            pos_timer.stop()

    chat.toggle_visibility = tracked_toggle

    # 托盘图标双击/菜单切换
    tray.connect_toggle(lambda: chat.toggle_visibility())

    # 托盘"显示小赫" → 恢复显示
    def on_show_pet():
        pet.show()
        pet.raise_()
    tray.show_pet_clicked.connect(on_show_pet)

    # ── 上下文信息更新 ──

    def update_context():
        """计算并更新上下文长度显示。"""
        msgs = chat_mgr.messages
        # 排除 system prompt
        user_msgs = [m for m in msgs if m["role"] != "system"]
        char_count = sum(len(m.get("content", "") or "") for m in msgs)
        chat.update_context_info(len(user_msgs), char_count)

    # ── 聊天消息处理 ──

    def on_message_sent(text: str):
        """用户发送消息后，调用 API。"""
        logger.info("用户发送: %s", text)
        pet.start_thinking()
        chat._send_btn.setEnabled(False)
        chat._send_btn.setText("...")
        update_context()  # 更新上下文显示

        worker = chat_mgr.send_message(text)

        # 开始 Hermes 流式消息
        chat.start_hermes_message()

        worker.text_chunk.connect(lambda t: chat.append_streaming_text(t))
        worker.finished.connect(on_response_finished)
        worker.error.connect(on_response_error)

        worker.start()

    def on_response_finished():
        """API 响应完成。"""
        reply_text = chat.finish_streaming()
        if reply_text:
            chat_mgr.append_assistant_reply(reply_text)
            logger.info("Hermes 回复: %s", reply_text[:80])
            # 语音播报
            if chat.voice_enabled():
                speak_text(reply_text)
        pet.stop_thinking()
        chat._send_btn.setEnabled(True)
        chat._send_btn.setText("发送")
        update_context()

    def on_response_error(err: str):
        """API 请求出错。"""
        chat.finish_streaming()
        chat.add_error_message(err)
        pet.stop_thinking()
        chat._send_btn.setEnabled(True)
        chat._send_btn.setText("发送")
        logger.error("API 错误: %s", err)

    # ── 语音播报 ──

    _tts_worker = None

    def speak_text(text: str):
        """播放语音。"""
        nonlocal _tts_worker
        # 截断过长文本（避免生成太慢）
        if len(text) > 500:
            text = text[:500] + "..."
        logger.info("TTS: 开始播报，文本长度=%d", len(text))
        _tts_worker = TTSSpeaker(text)
        _tts_worker.finished.connect(lambda: logger.info("TTS: 播报完成"))
        _tts_worker.error.connect(lambda e: logger.warning("TTS 错误: %s", e))
        _tts_worker.start()

    # ── 语音输入（麦克风） ──

    _stt_worker = None

    def on_mic_clicked():
        """麦克风按钮点击 → 开始录音识别。"""
        nonlocal _stt_worker
        _stt_worker = STTListener()
        _stt_worker.result.connect(on_stt_result)
        _stt_worker.finished.connect(chat.mic_recording_done)
        _stt_worker.error.connect(chat.mic_recording_error)
        _stt_worker.start()

    def on_stt_result(text: str):
        """语音识别完成 → 自动发送。"""
        logger.info("语音输入: %s", text)
        chat.add_user_message(text)
        on_message_sent(text)

    chat.mic_clicked.connect(on_mic_clicked)

    chat.message_sent.connect(on_message_sent)

    # ── 重启功能 ──

    def on_restart():
        """重启应用。"""
        import subprocess
        logger.info("重启应用...")
        # 获取当前脚本路径
        script_path = os.path.abspath(sys.argv[0])
        # 启动新进程
        subprocess.Popen([sys.executable, script_path])
        # 退出当前进程
        app.quit()

    chat.restart_clicked.connect(on_restart)
    tray.restart_clicked.connect(on_restart)

    # ── 昀示 ──
    pet.show()
    tray.show()

    logger.info("Hermes Desktop Pet 已启动")
    sys.exit(app.exec_())


if __name__ == "__main__":
    import traceback

    # 捕获 Qt 事件循环中的未处理异常
    def excepthook(exc_type, exc_value, exc_tb):
        with open("crash.log", "w", encoding="utf-8") as f:
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    sys.excepthook = excepthook

    main()
