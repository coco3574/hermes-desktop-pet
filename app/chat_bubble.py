"""聊天气泡组件 — 对话界面（支持文字选择 + 窗口缩放）"""

from typing import Optional, List

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QPen, QBrush, QCursor, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QScrollArea, QLabel, QFrame, QApplication, QSizePolicy
)

from . import config
from .personas import persona_manager
from .themes import get_current_theme, on_theme_change


# 缩放方向常量
_RESIZE_MARGIN = 8  # 边缘拖拽区域宽度


class MessageLabel(QLabel):
    """单条消息标签，支持圆角背景和文字选择。"""

    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.setWordWrap(True)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )
        self.setMargin(0)

        font = QFont(config.FONT_FAMILY, config.FONT_SIZE_CHAT)
        self.setFont(font)

        self._full_text = text
        self.setText(text)
        self._apply_style()

    def _apply_style(self):
        theme = get_current_theme()
        bg = theme.user_msg if self.is_user else theme.hermes_msg
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {theme.text};
                border-radius: 12px;
                padding: 8px 12px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_CHAT}px;
                selection-background-color: {theme.accent_light};
            }}
        """)


class StreamingLabel(QLabel):
    """Hermes 流式回复标签，支持逐字追加，结束后可选中复制。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._buffer = ""
        self._finished = False
        self.setWordWrap(True)
        font = QFont(config.FONT_FAMILY, config.FONT_SIZE_CHAT)
        self.setFont(font)
        theme = get_current_theme()
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {theme.hermes_msg};
                color: {theme.text};
                border-radius: 12px;
                padding: 8px 12px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_CHAT}px;
                selection-background-color: {theme.accent_light};
            }}
        """)
        self.setText("")

    def append_text(self, text: str):
        self._buffer += text
        self.setText(self._buffer)

    def get_full_text(self) -> str:
        return self._buffer

    def finish(self):
        """流式结束，启用文字选择。"""
        self._finished = True
        self.setText(self._buffer)
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )


class ChatBubble(QWidget):
    """聊天气泡窗口，支持文字复制和手动缩放。"""
    # 信号：用户发送了消息 / 语音输入 / 语音开关 / 重启
    message_sent = pyqtSignal(str)
    mic_clicked = pyqtSignal()        # 麦克风按钮点击
    voice_toggled = pyqtSignal(bool)  # 语音播报开关
    restart_clicked = pyqtSignal()    # 重启按钮点击

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hermes 聊天")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 最小尺寸 + 可缩放
        self.setMinimumSize(280, 360)
        self.resize(config.CHAT_WIDTH, config.CHAT_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 缩放状态
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        self._hover_edge = None  # 悬停的边缘

        # 记录初始尺寸用于计算缩放比例
        self._base_width = config.CHAT_WIDTH
        self._base_height = config.CHAT_HEIGHT
        self._base_font_size = config.FONT_SIZE_CHAT
        self._base_input_font_size = config.FONT_SIZE_INPUT

        self._streaming_label: Optional[StreamingLabel] = None
        self._message_labels: list[MessageLabel] = []  # 追踪所有消息标签
        self._setup_ui()
        
        # 注册主题变更回调
        on_theme_change(self.update_theme)

    def _setup_ui(self):
        theme = get_current_theme()
        
        # 外层容器 — 用布局填充整个窗口，跟随缩放
        self._container = QWidget(self)
        self._container.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.bubble_bg};
                border: 1.5px solid {theme.bubble_border};
                border-radius: 16px;
            }}
        """)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self._container)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # 标题栏（可拖拽移动窗口）
        self._title_bar = QWidget()
        self._title_bar.setFixedHeight(32)
        self._title_bar.setStyleSheet("background: transparent; border: none;")
        title_layout = QHBoxLayout(self._title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("💬 Hermes 助手")
        title_label.setFont(QFont(config.FONT_FAMILY, 13, QFont.Bold))
        title_label.setStyleSheet(f"color: {theme.text}; border: none; background: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 重启按钮
        restart_btn = QPushButton("🔄")
        restart_btn.setFixedSize(28, 28)
        restart_btn.setCursor(Qt.PointingHandCursor)
        restart_btn.setToolTip("重启应用")
        restart_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 14px; color: #999; border-radius: 14px;
            }
            QPushButton:hover { background-color: #E8DEF8; color: #666; }
        """)
        restart_btn.clicked.connect(self._on_restart)
        title_layout.addWidget(restart_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                font-size: 16px; color: #999; border-radius: 14px;
            }
            QPushButton:hover { background-color: #FF6B6B; color: white; }
        """)
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)
        layout.addWidget(self._title_bar)

        # 上下文信息栏
        self._context_label = QLabel("")
        self._context_label.setFont(QFont(config.FONT_FAMILY, 10))
        self._context_label.setStyleSheet(
            f"color: {theme.text_secondary}; border: none; background: transparent; padding: 0 4px;"
        )
        layout.addWidget(self._context_label)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {theme.bubble_border}; max-height: 1px; border: none;")
        layout.addWidget(sep)

        # 消息滚动区域
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #C0B0D0; border-radius: 3px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        self._msg_container = QWidget()
        self._msg_container.setStyleSheet("background: transparent; border: none;")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(4, 4, 4, 4)
        self._msg_layout.setSpacing(8)
        self._msg_layout.addStretch()

        self._scroll.setWidget(self._msg_container)
        layout.addWidget(self._scroll, 1)

        # 底部输入区域
        input_bar = QHBoxLayout()
        input_bar.setSpacing(6)

        self._input = QTextEdit()
        self._input.setPlaceholderText("输入消息...")
        self._input.setFixedHeight(44)
        self._input.setFont(QFont(config.FONT_FAMILY, config.FONT_SIZE_INPUT))
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.input_bg};
                border: 1.5px solid {theme.input_border};
                border-radius: 12px;
                padding: 6px 12px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_INPUT}px;
                color: {theme.text};
            }}
            QTextEdit:focus {{ border-color: {theme.send_btn}; }}
        """)
        self._input.installEventFilter(self)
        input_bar.addWidget(self._input, 1)

        self._send_btn = QPushButton("发送")
        self._send_btn.setFixedSize(60, 44)
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.setFont(QFont(config.FONT_FAMILY, config.FONT_SIZE_INPUT, QFont.Bold))
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.send_btn};
                color: white; border: none; border-radius: 12px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_INPUT}px;
            }}
            QPushButton:hover {{ background-color: {theme.send_btn_hover}; }}
            QPushButton:pressed {{ background-color: {theme.accent}; }}
        """)
        self._send_btn.clicked.connect(self._on_send)
        input_bar.addWidget(self._send_btn)

        # 麦克风按钮
        self._mic_btn = QPushButton("🎤")
        self._mic_btn.setFixedSize(44, 44)
        self._mic_btn.setCursor(Qt.PointingHandCursor)
        self._mic_btn.setToolTip("语音输入（点击后说话）")
        self._mic_btn.setStyleSheet("""
            QPushButton {
                background-color: #F0E6FF;
                border: 1.5px solid #D0C0E0;
                border-radius: 12px;
                font-size: 18px;
            }
            QPushButton:hover { background-color: #E0D0F5; }
            QPushButton:pressed { background-color: #D0C0E8; }
        """)
        self._mic_btn.clicked.connect(self._on_mic)
        input_bar.addWidget(self._mic_btn)

        # 语音播报开关
        self._voice_btn = QPushButton("🔊")
        self._voice_btn.setFixedSize(44, 44)
        self._voice_btn.setCursor(Qt.PointingHandCursor)
        self._voice_btn.setToolTip("语音播报开关")
        self._voice_btn.setCheckable(True)
        self._voice_btn.setChecked(True)
        self._voice_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8F5E9;
                border: 1.5px solid #C8E6C9;
                border-radius: 12px;
                font-size: 18px;
            }
            QPushButton:checked { background-color: #C8E6C9; border-color: #A5D6A7; }
            QPushButton:hover { background-color: #DCEDC8; }
        """)
        self._voice_btn.clicked.connect(self._on_voice_toggle)
        input_bar.addWidget(self._voice_btn)

        layout.addLayout(input_bar)

    # ── 标题栏拖拽移动窗口 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 检查是否在边缘区域（缩放）
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resize_edge = edge
                self._resize_start_pos = event.globalPos()
                self._resize_start_geo = self.geometry()
                event.accept()
                return

            # 标题栏区域拖拽移动
            if event.pos().y() < self._title_bar.height() + 10:
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            # 缩放处理
            if self._resize_edge and self._resize_start_geo:
                self._do_resize(event.globalPos())
                event.accept()
                return

            # 拖拽移动
            if hasattr(self, '_drag_pos') and self._drag_pos:
                self.move(event.globalPos() - self._drag_pos)
                event.accept()
                return

        # 更新鼠标样式（悬停边缘时）
        edge = self._get_resize_edge(event.pos())
        if edge != self._hover_edge:
            self._hover_edge = edge
            self.update()  # 触发重绘
        if edge:
            cursors = {
                "left": Qt.SizeHorCursor, "right": Qt.SizeHorCursor,
                "top": Qt.SizeVerCursor, "bottom": Qt.SizeVerCursor,
                "top-left": Qt.SizeFDiagCursor, "top-right": Qt.SizeBDiagCursor,
                "bottom-left": Qt.SizeBDiagCursor, "bottom-right": Qt.SizeFDiagCursor,
            }
            self.setCursor(cursors.get(edge, Qt.ArrowCursor))
        else:
            self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geo = None
        if hasattr(self, '_drag_pos'):
            self._drag_pos = None
        event.accept()

    def leaveEvent(self, event):
        """鼠标离开窗口时清除边缘高亮。"""
        if self._hover_edge:
            self._hover_edge = None
            self.setCursor(Qt.ArrowCursor)
            self.update()

    def _get_resize_edge(self, pos: QPoint) -> Optional[str]:
        """判断鼠标位置是否在窗口边缘。"""
        w, h = self.width(), self.height()
        m = _RESIZE_MARGIN
        x, y = pos.x(), pos.y()

        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m

        if top and left: return "top-left"
        if top and right: return "top-right"
        if bottom and left: return "bottom-left"
        if bottom and right: return "bottom-right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return None

    def _do_resize(self, global_pos: QPoint):
        """执行缩放。"""
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()
        geo = self._resize_start_geo
        min_w, min_h = self.minimumWidth(), self.minimumHeight()

        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()

        edge = self._resize_edge
        if "right" in edge:
            w = max(min_w, geo.width() + dx)
        if "bottom" in edge:
            h = max(min_h, geo.height() + dy)
        if "left" in edge:
            new_w = max(min_w, geo.width() - dx)
            x = geo.x() + geo.width() - new_w
            w = new_w
        if "top" in edge:
            new_h = max(min_h, geo.height() - dy)
            y = geo.y() + geo.height() - new_h
            h = new_h

        self.setGeometry(x, y, w, h)
        
        # 根据窗口大小调整字体
        self._update_fonts_on_resize(w, h)

    def _update_fonts_on_resize(self, width: int, height: int):
        """根据窗口大小动态调整字体。"""
        # 计算缩放比例（基于宽度）
        scale = width / self._base_width
        scale = max(0.6, min(scale, 2.0))  # 限制缩放范围
        
        # 计算新字体大小
        new_chat_font_size = max(10, int(self._base_font_size * scale))
        new_input_font_size = max(10, int(self._base_input_font_size * scale))
        
        # 更新消息标签的样式
        msg_style = f"""
            QLabel {{
                background-color: {config.COLOR_HERMES_MSG};
                color: {config.COLOR_TEXT};
                border-radius: 12px;
                padding: 8px 12px;
                font-family: {config.FONT_FAMILY};
                font-size: {new_chat_font_size}px;
                selection-background-color: #C8A8E8;
            }}
        """
        user_style = f"""
            QLabel {{
                background-color: {config.COLOR_USER_MSG};
                color: {config.COLOR_TEXT};
                border-radius: 12px;
                padding: 8px 12px;
                font-family: {config.FONT_FAMILY};
                font-size: {new_chat_font_size}px;
                selection-background-color: #C8A8E8;
            }}
        """
        
        for label in self._message_labels:
            if hasattr(label, 'is_user') and label.is_user:
                label.setStyleSheet(user_style)
            else:
                label.setStyleSheet(msg_style)
        
        # 更新流式标签的样式
        if self._streaming_label:
            self._streaming_label.setStyleSheet(msg_style)
        
        # 更新输入框和按钮的字体
        self._input.setFont(QFont(config.FONT_FAMILY, new_input_font_size))
        self._send_btn.setFont(QFont(config.FONT_FAMILY, new_input_font_size, QFont.Bold))

    # ── 其他逻辑 ──

    def eventFilter(self, obj, event):
        from PyQt5.QtCore import QEvent
        if obj is self._input and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if not (event.modifiers() & Qt.ShiftModifier):
                    self._on_send()
                    return True
        return super().eventFilter(obj, event)

    def _on_send(self):
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        self.add_user_message(text)
        self.message_sent.emit(text)

    def _on_mic(self):
        """麦克风按钮点击。"""
        self._mic_btn.setEnabled(False)
        self._mic_btn.setText("🔴")
        self._mic_btn.setToolTip("正在听...")
        self.mic_clicked.emit()

    def mic_recording_done(self):
        """录音结束，恢复按钮状态。"""
        self._mic_btn.setEnabled(True)
        self._mic_btn.setText("🎤")
        self._mic_btn.setToolTip("语音输入（点击后说话）")

    def mic_recording_error(self, msg: str):
        """录音出错。"""
        self.mic_recording_done()
        self.add_error_message(msg)

    def _on_voice_toggle(self):
        """语音播报开关切换。"""
        enabled = self._voice_btn.isChecked()
        self._voice_btn.setText("🔊" if enabled else "🔇")
        self._voice_btn.setToolTip("语音播报: " + ("开" if enabled else "关"))
        self.voice_toggled.emit(enabled)

    def _on_restart(self):
        """重启按钮点击。"""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "确认重启",
            "确定要重启应用吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.restart_clicked.emit()

    def voice_enabled(self) -> bool:
        return self._voice_btn.isChecked()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def add_user_message(self, text: str):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        w_layout = QHBoxLayout(wrapper)
        w_layout.setContentsMargins(30, 2, 0, 2)

        label = MessageLabel(text, is_user=True)
        label.setMaximumWidth(260)
        self._message_labels.append(label)  # 追踪标签
        w_layout.addWidget(label)
        w_layout.addStretch()

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, wrapper)
        self._scroll_to_bottom()

    def _get_persona_avatar(self) -> Optional[QPixmap]:
        """获取当前人格的头像图片（裁剪后缩放到 28x28）"""
        current_persona = persona_manager.get_current()
        if not current_persona or not current_persona.skin:
            return None
        
        import os
        # 构建图片路径
        assets_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets"
        )
        sprite_path = os.path.join(assets_dir, current_persona.skin)
        
        if not os.path.exists(sprite_path):
            return None
        
        try:
            original = QPixmap(sprite_path)
            if original.isNull():
                return None
            
            # 裁剪空白边缘
            img = original.toImage()
            w, h = img.width(), img.height()
            min_x, min_y, max_x, max_y = w, h, 0, 0
            for y in range(h):
                for x in range(w):
                    pixel = img.pixelColor(x, y)
                    # 跳过接近白色/透明的像素
                    if pixel.alpha() > 30 and not (
                        pixel.red() > 240 and pixel.green() > 240 and pixel.blue() > 240
                    ):
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)
            
            if max_x > min_x and max_y > min_y:
                cropped = original.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
            else:
                cropped = original
            
            # 缩放到 28x28，保持比例
            return cropped.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception:
            return None

    def start_hermes_message(self):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        w_layout = QHBoxLayout(wrapper)
        w_layout.setContentsMargins(0, 2, 30, 2)

        # 尝试加载皮肤头像，失败则用默认 emoji
        avatar_pixmap = self._get_persona_avatar()
        
        avatar = QLabel()
        avatar.setFixedSize(28, 28)
        avatar.setAlignment(Qt.AlignCenter)
        
        if avatar_pixmap and not avatar_pixmap.isNull():
            avatar.setPixmap(avatar_pixmap)
            avatar.setStyleSheet("""
                QLabel {
                    background-color: #F0E6FF;
                    border-radius: 14px;
                    border: none;
                    padding: 2px;
                }
            """)
        else:
            avatar.setText("🌸")
            avatar.setStyleSheet("""
                QLabel {
                    background-color: #F0E6FF;
                    border-radius: 14px;
                    font-size: 14px;
                    border: none;
                }
            """)
        
        w_layout.addWidget(avatar, 0, Qt.AlignTop)

        self._streaming_label = StreamingLabel()
        self._streaming_label.setMinimumWidth(60)
        self._streaming_label.setMaximumWidth(260)
        w_layout.addWidget(self._streaming_label, 1)
        w_layout.addStretch()

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, wrapper)
        self._scroll_to_bottom()
        return self._streaming_label

    def append_streaming_text(self, text: str):
        if self._streaming_label:
            self._streaming_label.append_text(text)
            self._scroll_to_bottom()

    def finish_streaming(self):
        if self._streaming_label:
            self._streaming_label.finish()
            reply_text = self._streaming_label.get_full_text()
            self._message_labels.append(self._streaming_label)  # 追踪标签
            self._streaming_label = None
            return reply_text
        return ""

    def add_error_message(self, text: str):
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent; border: none;")
        w_layout = QHBoxLayout(wrapper)
        w_layout.setContentsMargins(0, 2, 30, 2)

        label = QLabel(f"⚠️ {text}")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setFont(QFont(config.FONT_FAMILY, config.FONT_SIZE_LABEL))
        label.setStyleSheet("""
            QLabel {
                background-color: #FFF0F0;
                color: #CC4444;
                border: 1px solid #FFD0D0;
                border-radius: 10px;
                padding: 8px 12px;
            }
        """)
        label.setMaximumWidth(280)
        w_layout.addWidget(label)
        w_layout.addStretch()

        self._msg_layout.insertWidget(self._msg_layout.count() - 1, wrapper)
        self._scroll_to_bottom()

    def update_context_info(self, msg_count: int, char_count: int):
        est_tokens = int(char_count * 1.2)
        self._context_label.setText(f"💬 {msg_count} 条消息 · ~{est_tokens} tokens")

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._hover_edge:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m = _RESIZE_MARGIN
        w, h = self.width(), self.height()
        color = QColor(176, 136, 192, 120)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        edge = self._hover_edge
        if "left" in edge:
            p.drawRect(0, 0, m, h)
        if "right" in edge:
            p.drawRect(w - m, 0, m, h)
        if "top" in edge:
            p.drawRect(0, 0, w, m)
        if "bottom" in edge:
            p.drawRect(0, h - m, w, m)
        p.end()

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
            self._input.setFocus()
    
    def update_theme(self, theme=None):
        """更新主题样式"""
        if theme is None:
            theme = get_current_theme()
        
        # 更新容器背景
        self._container.setStyleSheet(f"""
            QWidget {{
                background-color: {theme.bubble_bg};
                border: 1.5px solid {theme.bubble_border};
                border-radius: 16px;
            }}
        """)
        
        # 更新标题栏颜色
        for child in self._title_bar.findChildren(QLabel):
            child.setStyleSheet(f"color: {theme.text}; border: none; background: transparent;")
        
        # 更新上下文信息栏
        self._context_label.setStyleSheet(
            f"color: {theme.text_secondary}; border: none; background: transparent; padding: 0 4px;"
        )
        
        # 更新输入框
        self._input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.input_bg};
                border: 1.5px solid {theme.input_border};
                border-radius: 12px;
                padding: 6px 12px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_INPUT}px;
                color: {theme.text};
            }}
            QTextEdit:focus {{ border-color: {theme.send_btn}; }}
        """)
        
        # 更新发送按钮
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.send_btn};
                color: white; border: none; border-radius: 12px;
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE_INPUT}px;
            }}
            QPushButton:hover {{ background-color: {theme.send_btn_hover}; }}
            QPushButton:pressed {{ background-color: {theme.accent}; }}
        """)
        
        # 更新所有消息标签样式
        for label in self._message_labels:
            if hasattr(label, '_apply_style'):
                label._apply_style()
        
        # 更新流式标签
        if self._streaming_label:
            self._streaming_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {theme.hermes_msg};
                    color: {theme.text};
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-family: {config.FONT_FAMILY};
                    font-size: {config.FONT_SIZE_CHAT}px;
                    selection-background-color: {theme.accent_light};
                }}
            """)
    
    def clear_messages(self):
        """清空所有聊天消息（人格切换时调用）"""
        # 遍历并删除所有消息 widget（保留最后的 stretch）
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 重置流式标签和追踪列表
        self._streaming_label = None
        self._message_labels.clear()
        
        # 重新添加欢迎消息
        self._add_welcome_message()
    
    def _add_welcome_message(self):
        """添加欢迎消息"""
        current_persona = persona_manager.get_current()
        if current_persona:
            welcome_text = f"你好，我是{current_persona.name}，有什么可以帮你的？"
        else:
            welcome_text = "你好，有什么可以帮你的？"
        
        # 使用 Hermes 格式添加消息
        self.start_hermes_message()
        self._streaming_label.append_text(welcome_text)
        self._streaming_label.finish()
