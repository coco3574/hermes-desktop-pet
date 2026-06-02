"""桌面宠物主窗口 — 单帧插画 + 程序化动画 + 点击互动"""

import os
import math
import random
from typing import Optional

from PyQt5.QtCore import Qt, QPoint, QTimer, QRect, QPointF, pyqtSignal
from PyQt5.QtGui import (
    QPixmap, QPainter, QColor, QFont, QPen, QBrush,
    QPainterPath, QTransform, QRegion
)
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QApplication, QLabel

from . import config
from .personas import persona_manager
from .greeting_bubble import GreetingBubble


class PetWindow(QWidget):
    """透明无边框桌面宠物窗口，显示小天使插画 + 程序化动画。"""
    
    # 信号：人格切换（通知 main.py 更新 API 配置）
    persona_changed = pyqtSignal(str)  # 传递人格 ID
    
    # 皮肤注册表：名称 → 图片文件名（兼容旧版）
    SKINS = {
        "小天使": "angel_sprite.png",
        "帅仓鼠": "hamster.png",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hermes Desktop Pet")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 拖拽状态
        self._drag_pos: Optional[QPoint] = None
        self._drag_moved = False

        # 从 persona_manager 加载当前人格
        current_persona = persona_manager.get_current()
        self._current_skin = current_persona.skin if current_persona else "angel_sprite.png"
        self._greetings = current_persona.greetings if current_persona else self._default_greetings()
        self._theme_color = current_persona.theme_color if current_persona else "#B088C0"

        # 加载角色图片
        self._pixmap: Optional[QPixmap] = None
        self._load_character()

        # 动画参数
        self._anim_tick = 0          # 动画计时器
        self._bob_offset_y = 0       # 上下浮动偏移
        self._blink_timer = 0        # 眨眼计时
        self._is_blinking = False
        self._breath_scale = 1.0     # 呼吸缩放
        self._bounce_y = 0           # 点击弹跳
        self._bounce_vy = 0          # 弹跳速度

        # 动画定时器 — 33ms ≈ 30fps
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.setInterval(33)

        # 独立的问候气泡窗口
        self._greeting_bubble = GreetingBubble()
        
        # 思考状态
        self._thinking = False

        # 随机行为定时器（眨眼、歪头等）
        self._random_action_timer = QTimer(self)
        self._random_action_timer.timeout.connect(self._random_action)
        self._random_action_timer.start(random.randint(2000, 5000))

        # 放置到屏幕右下角
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 40,
                  screen.height() - self.height() - 60)

        # 启动动画
        self._anim_timer.start()

    def _load_character(self):
        """加载角色插画（单帧 PNG，自动裁剪空白边缘）。"""
        # 支持两种方式：1) SKINS 字典中的名称 2) 直接文件名
        if self._current_skin in self.SKINS:
            filename = self.SKINS[self._current_skin]
        else:
            # 直接使用文件名（人格切换时使用）
            filename = self._current_skin
        
        sprite_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets", filename
        )
        if not os.path.exists(sprite_path):
            print(f"[Pet] 形象图片不存在: {sprite_path}")
            self.setFixedSize(config.PET_WIDTH, config.PET_HEIGHT)
            return

        original = QPixmap(sprite_path)
        # 自动裁剪空白边缘（灰白色背景）
        self._pixmap = self._trim_whitespace(original)

        # 缩放到目标高度，保持比例
        target_h = config.PET_HEIGHT
        aspect = self._pixmap.width() / self._pixmap.height()
        target_w = max(int(target_h * aspect), 60)
        self.setFixedSize(target_w, target_h)
        print(f"[Pet] 加载形象: {filename}")

    def _trim_whitespace(self, pixmap: QPixmap) -> QPixmap:
        """裁剪图片四周的灰白背景，保留核心内容。"""
        from PyQt5.QtGui import QImage
        img = pixmap.toImage()
        w, h = img.width(), img.height()

        # 采样四个角获取背景色
        corners = [
            img.pixelColor(0, 0),
            img.pixelColor(w - 1, 0),
            img.pixelColor(0, h - 1),
            img.pixelColor(w - 1, h - 1),
        ]
        # 取左上角作为背景参考色
        bg = corners[0]
        bg_r, bg_g, bg_b = bg.red(), bg.green(), bg.blue()

        def is_bg_pixel(x, y):
            c = img.pixelColor(x, y)
            return (abs(c.red() - bg_r) < 25 and
                    abs(c.green() - bg_g) < 25 and
                    abs(c.blue() - bg_b) < 25)

        # 找内容边界
        top = 0
        for y in range(h):
            if not all(is_bg_pixel(x, y) for x in range(0, w, max(1, w // 20))):
                top = y
                break

        bottom = h - 1
        for y in range(h - 1, -1, -1):
            if not all(is_bg_pixel(x, y) for x in range(0, w, max(1, w // 20))):
                bottom = y
                break

        left = 0
        for x in range(w):
            if not all(is_bg_pixel(x, y) for y in range(0, h, max(1, h // 20))):
                left = x
                break

        right = w - 1
        for x in range(w - 1, -1, -1):
            if not all(is_bg_pixel(x, y) for y in range(0, h, max(1, h // 20))):
                right = x
                break

        # 加一点边距
        margin = 5
        left = max(0, left - margin)
        top = max(0, top - margin)
        right = min(w - 1, right + margin)
        bottom = min(h - 1, bottom + margin)

        crop_w = right - left + 1
        crop_h = bottom - top + 1
        if crop_w < 20 or crop_h < 20:
            return pixmap  # 裁剪异常，返回原图

        cropped = pixmap.copy(left, top, crop_w, crop_h)
        print(f"[Pet] 裁剪: 原图 {w}x{h} → 内容 {crop_w}x{crop_h} (offset: {left},{top})")
        return cropped

    # ── 程序化动画 ──

    def _animate(self):
        """每帧更新动画参数。"""
        self._anim_tick += 1
        t = self._anim_tick

        # 上下浮动（正弦波，周期约2秒）
        self._bob_offset_y = math.sin(t * 0.08) * 4

        # 呼吸缩放（很微小，周期约3秒）
        self._breath_scale = 1.0 + math.sin(t * 0.05) * 0.008

        # 弹跳物理
        if abs(self._bounce_vy) > 0.1 or abs(self._bounce_y) > 0.1:
            self._bounce_vy += 0.8  # 重力
            self._bounce_y += self._bounce_vy
            if self._bounce_y > 0:
                self._bounce_y = 0
                self._bounce_vy = -self._bounce_vy * 0.4  # 反弹衰减
                if abs(self._bounce_vy) < 1:
                    self._bounce_vy = 0

        # 思考时抖动
        if self._thinking:
            import math as m
            self._bob_offset_y += math.sin(t * 0.3) * 2

        self.update()

    def _random_action(self):
        """随机行为：眨眼等。"""
        if random.random() < 0.6:
            self._is_blinking = True
            QTimer.singleShot(150, self._unblink)

        # 下次随机行为间隔
        self._random_action_timer.setInterval(random.randint(2000, 6000))

    def _unblink(self):
        self._is_blinking = False

    # ── 思考动画控制 ──

    def start_thinking(self):
        self._thinking = True
        self.update()

    def stop_thinking(self):
        self._thinking = False
        self.update()

    # ── 问候气泡 ──

    def _default_greetings(self):
        """默认问候语"""
        return [
            "你好呀～(◕ᴗ◕✿)",
            "有什么需要帮忙的吗？",
            "我在呢，说吧～",
        ]

    def show_greeting(self):
        """显示随机问候语。"""
        greeting_text = random.choice(self._greetings)
        # 弹跳效果
        self._bounce_vy = -8
        self.update()
        # 使用独立气泡显示
        self._greeting_bubble.show_message(greeting_text, self, duration=3000)

    # ── 皮肤切换 ──

    def switch_skin(self, skin_name: str):
        """切换到指定皮肤（兼容旧版）。"""
        if skin_name in self.SKINS and skin_name != self._current_skin:
            self._current_skin = skin_name
            self._load_character()
            self.update()
            
            # 同步更新 persona_manager 中当前人格的 skin
            current_persona = persona_manager.get_current()
            if current_persona:
                # 找到对应的文件名
                filename = self.SKINS.get(skin_name, skin_name)
                current_persona.skin = filename
                persona_manager._save()
            
            # 发送信号通知聊天窗口更新头像
            if current_persona:
                self.persona_changed.emit(current_persona.id)
            
            print(f"[Pet] 切换皮肤: {skin_name}")
    
    def switch_persona(self, persona_id: str):
        """切换到指定人格"""
        if persona_manager.switch_to(persona_id):
            persona = persona_manager.get_current()
            if persona:
                # 更新形象
                self._current_skin = persona.skin
                self._load_character()
                
                # 更新问候语
                self._greetings = persona.greetings or self._default_greetings()
                
                # 更新主题色
                self._theme_color = persona.theme_color
                
                # 发送信号通知 main.py 更新 API 配置
                self.persona_changed.emit(persona_id)
                
                # 显示切换成功问候
                self.show_greeting()
                
                print(f"[Pet] 切换人格: {persona.name}")

    # ── 鼠标事件 ──

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._drag_moved = False
            event.accept()
        elif event.button() == Qt.RightButton:
            # 右键不处理拖拽，让 contextMenuEvent 触发
            pass

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            self._drag_moved = True
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._drag_pos and not self._drag_moved:
                self._on_click()
            self._drag_pos = None
            event.accept()

    def _on_click(self):
        """点击角色。"""
        self.show_greeting()

    def contextMenuEvent(self, event):
        """右键菜单"""
        try:
            from PyQt5.QtWidgets import QMenu, QAction
            from .themes import get_current_theme, get_all_themes, set_theme

            theme = get_current_theme()
            menu = QMenu(self)
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {theme.bubble_bg};
                    border: 1.5px solid {theme.bubble_border};
                    border-radius: 12px;
                    padding: 6px;
                    font-family: 'Microsoft YaHei';
                    font-size: 13px;
                    color: {theme.text};
                }}
                QMenu::item {{
                    padding: 8px 24px 8px 12px;
                    border-radius: 8px;
                    margin: 2px 4px;
                }}
                QMenu::item:selected {{
                    background-color: {theme.accent_light};
                }}
                QMenu::separator {{
                    height: 1px;
                    background: {theme.bubble_border};
                    margin: 4px 8px;
                }}
                QMenu::item:disabled {{
                    color: {theme.text_secondary};
                }}
            """)

            # 显示/隐藏聊天
            toggle_action = QAction("💬  显示/隐藏聊天", self)
            toggle_action.triggered.connect(self._toggle_chat)
            menu.addAction(toggle_action)

            # 隐藏
            hide_action = QAction("👋  隐藏小赫", self)
            hide_action.triggered.connect(self._hide_all)
            menu.addAction(hide_action)

            menu.addSeparator()

            # 人格切换
            personas = persona_manager.get_all()
            if len(personas) > 1:
                current = persona_manager.get_current()
                persona_menu = menu.addMenu("🔄  切换人格")
                for persona in personas:
                    action = QAction(persona.name, self)
                    action.setCheckable(True)
                    action.setChecked(current and persona.id == current.id)
                    action.triggered.connect(lambda checked, pid=persona.id: self.switch_persona(pid))
                    persona_menu.addAction(action)
            else:
                persona_menu = menu.addMenu("🔄  切换人格")
                action = QAction(personas[0].name if personas else "默认", self)
                action.setCheckable(True)
                action.setChecked(True)
                action.setEnabled(False)
                persona_menu.addAction(action)

            # 皮肤切换
            skin_menu = menu.addMenu("👗  切换皮肤")
            for skin_name in self.SKINS:
                action = QAction(skin_name, self)
                action.setCheckable(True)
                action.setChecked(skin_name == self._current_skin)
                action.triggered.connect(lambda checked, n=skin_name: self.switch_skin(n))
                skin_menu.addAction(action)

            # 主题切换
            theme_menu = menu.addMenu("🎨  切换主题")
            for t in get_all_themes():
                action = QAction(t.name, self)
                action.setCheckable(True)
                action.setChecked(t.id == theme.id)
                action.triggered.connect(lambda checked, tid=t.id: set_theme(tid))
                theme_menu.addAction(action)

            menu.addSeparator()

            # 会话管理
            from .sessions import session_manager
            session_menu = menu.addMenu("💬  会话管理")
            
            # 新建会话
            new_session_action = QAction("📝  新建会话", self)
            new_session_action.triggered.connect(self._on_new_session)
            session_menu.addAction(new_session_action)
            
            session_menu.addSeparator()
            
            # 会话列表
            sessions = session_manager.get_all_sessions()
            if sessions:
                current_session = session_manager.get_current()
                for session in sessions[:10]:  # 最多显示 10 个
                    # 格式化时间
                    import time
                    time_str = time.strftime("%m-%d %H:%M", time.localtime(session.updated_at))
                    action = QAction(f"📌 {session.name[:20]}... ({time_str})", self)
                    action.setCheckable(True)
                    action.setChecked(current_session and session.id == current_session.id)
                    action.triggered.connect(lambda checked, sid=session.id: self._on_load_session(sid))
                    session_menu.addAction(action)
            else:
                no_session_action = QAction("暂无历史会话", self)
                no_session_action.setEnabled(False)
                session_menu.addAction(no_session_action)

            menu.addSeparator()

            # 设置
            settings_action = QAction("⚙️  设置", self)
            settings_action.triggered.connect(self._open_persona_manager)
            menu.addAction(settings_action)

            # 退出
            quit_action = QAction("❌  退出", self)
            quit_action.triggered.connect(QApplication.quit)
            menu.addAction(quit_action)

            menu.exec_(event.globalPos())
        except Exception as e:
            print(f"[Pet] 右键菜单错误: {e}")
            import traceback
            traceback.print_exc()

    def _toggle_chat(self):
        pass

    def _hide_all(self):
        pass
    
    def _open_persona_manager(self):
        """打开人格管理对话框"""
        from .persona_dialog import PersonaListDialog
        dialog = PersonaListDialog(self)
        dialog.exec_()
    
    def _on_new_session(self):
        """新建会话"""
        if hasattr(self, '_chat_mgr'):
            self._chat_mgr.create_new_session()
            # 通知聊天窗口清空消息
            if hasattr(self, '_clear_chat_callback'):
                self._clear_chat_callback()
    
    def _on_load_session(self, session_id: str):
        """加载指定会话"""
        if hasattr(self, '_chat_mgr'):
            if self._chat_mgr.load_session(session_id):
                # 通知聊天窗口刷新消息
                if hasattr(self, '_refresh_chat_callback'):
                    self._refresh_chat_callback()

    # ── 绘制 ──

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._pixmap and not self._pixmap.isNull():
            # 计算绘制区域
            draw_h = self.height()
            draw_w = self.width()

            # 缩放角色图
            aspect = self._pixmap.width() / self._pixmap.height()
            target_h = int(draw_h * self._breath_scale)
            target_w = int(target_h * aspect)

            if target_w > draw_w:
                target_w = draw_w
                target_h = int(target_w / aspect)

            scaled = self._pixmap.scaled(
                target_w, target_h,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            # 居中 + 浮动 + 弹跳
            x = (draw_w - scaled.width()) // 2
            y = (draw_h - scaled.height()) // 2 + int(self._bob_offset_y + self._bounce_y)

            # 思考时轻微左右摇摆
            if self._thinking:
                x += int(math.sin(self._anim_tick * 0.15) * 3)

            painter.drawPixmap(x, y, scaled)

            # 眨眼效果：在眼睛区域画一个小遮罩（仅视觉提示）
            if self._is_blinking:
                # 在角色上方画两个小短线表示闭眼
                eye_y = y + int(target_h * 0.28)
                eye_lx = x + int(target_w * 0.40)
                eye_rx = x + int(target_w * 0.60)
                painter.setPen(QPen(QColor("#8B6FA8"), 2.5, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(eye_lx - 4, eye_y, eye_lx + 4, eye_y)
                painter.drawLine(eye_rx - 4, eye_y, eye_rx + 4, eye_y)

            # 绘制思考指示：头顶画省略号
            if self._thinking:
                dot_y = y - 12
                dot_x = x + target_w // 2
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor("#B088C0"))
                for i in range(3):
                    dx = dot_x + (i - 1) * 10
                    dy = dot_y + int(math.sin(self._anim_tick * 0.1 + i) * 3)
                    painter.drawEllipse(dx - 3, dy - 3, 6, 6)

        else:
            # 没有图片时绘制占位
            painter.setPen(QPen(QColor("#B088C0"), 2))
            painter.setBrush(QBrush(QColor("#F0E6FF")))
            painter.drawEllipse(10, 50, self.width() - 20, self.height() - 60)
            painter.setFont(QFont("Microsoft YaHei", 24))
            painter.drawText(self.rect(), Qt.AlignCenter, "👼")

        painter.end()
