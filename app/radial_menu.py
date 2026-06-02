"""径向菜单组件 — 环绕宠物的圆形按钮菜单（简化版）"""

import math
from typing import Callable
from dataclasses import dataclass

from PyQt5.QtCore import Qt, QPoint, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PyQt5.QtWidgets import QWidget, QApplication

from .themes import get_current_theme


@dataclass
class MenuItem:
    """菜单项"""
    icon: str           # emoji 图标
    label: str          # 显示文字
    callback: Callable  # 点击回调
    color: str = ""     # 自定义颜色（空则用主题色）


class RadialMenu(QWidget):
    """径向菜单 — 环绕点击位置的圆形按钮菜单"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._items: list[MenuItem] = []
        self._button_rects: list[QRect] = []  # 按钮区域
        self._hover_index: int = -1
        self._center_in_window = QPoint(0, 0)
        self._radius = 100  # 环绕半径
        self._btn_size = 56  # 按钮大小

    def show_at(self, center: QPoint, items: list[MenuItem]):
        """在指定位置显示菜单"""
        self._items = items
        self._button_rects.clear()
        self._hover_index = -1

        # 计算窗口大小（覆盖点击区域周围）
        margin = self._radius + self._btn_size + 20
        x = center.x() - margin
        y = center.y() - margin
        w = margin * 2
        h = margin * 2

        # 确保在屏幕内
        screen = QApplication.primaryScreen().geometry()
        x = max(screen.left(), min(x, screen.right() - w))
        y = max(screen.top(), min(y, screen.bottom() - h))

        self.setGeometry(x, y, w, h)

        # 计算按钮位置（相对于窗口）
        cx = center.x() - x
        cy = center.y() - y
        self._center_in_window = QPoint(cx, cy)

        count = len(items)
        angle_step = 360.0 / count if count > 0 else 0
        start_angle = -90  # 从正上方开始

        for i, item in enumerate(items):
            angle = math.radians(start_angle + i * angle_step)
            btn_x = cx + int(self._radius * math.cos(angle)) - self._btn_size // 2
            btn_y = cy + int(self._radius * math.sin(angle)) - self._btn_size // 2
            self._button_rects.append(QRect(btn_x, btn_y, self._btn_size, self._btn_size + 20))

        self.show()
        self.raise_()
        self.activateWindow()
        self.update()

    def paintEvent(self, event):
        """绘制菜单"""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 半透明背景
        p.fillRect(self.rect(), QColor(0, 0, 0, 60))

        theme = get_current_theme()
        accent = QColor(theme.accent)

        # 中心装饰
        cx = self._center_in_window.x()
        cy = self._center_in_window.y()

        # 外圈
        p.setPen(QPen(accent.lighter(150), 2, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(cx - 30, cy - 30, 60, 60)

        # 内圈
        p.setPen(QPen(accent, 2))
        p.drawEllipse(cx - 15, cy - 15, 30, 30)

        # 中心点
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(accent))
        p.drawEllipse(cx - 4, cy - 4, 8, 8)

        # 绘制按钮
        for i, (item, rect) in enumerate(zip(self._items, self._button_rects)):
            color = QColor(item.color) if item.color else accent
            is_hover = (i == self._hover_index)

            # 按钮圆形区域
            btn_rect = QRect(rect.x(), rect.y(), self._btn_size, self._btn_size)

            # 阴影
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(0, 0, 0, 30)))
            p.drawEllipse(btn_rect.adjusted(2, 2, 2, 2))

            # 按钮背景
            if is_hover:
                p.setBrush(QBrush(color.lighter(130)))
            else:
                p.setBrush(QBrush(color))

            p.setPen(QPen(color.darker(120), 1.5))
            p.drawEllipse(btn_rect)

            # 图标
            icon_font = QFont("Segoe UI Emoji", 16 if is_hover else 14)
            p.setFont(icon_font)
            p.setPen(Qt.white)
            icon_rect = QRect(btn_rect.x(), btn_rect.y() + 2, btn_rect.width(), btn_rect.height() - 10)
            p.drawText(icon_rect, Qt.AlignCenter, item.icon)

            # 文字标签
            label_font = QFont("Microsoft YaHei", 8)
            p.setFont(label_font)
            p.setPen(QColor(255, 255, 255, 220))
            label_rect = QRect(rect.x() - 10, rect.bottom() - 18, rect.width() + 20, 18)
            p.drawText(label_rect, Qt.AlignHCenter | Qt.AlignTop, item.label)

        p.end()

    def mouseMoveEvent(self, event):
        """鼠标移动 — 检测悬停"""
        pos = event.pos()
        old_hover = self._hover_index
        self._hover_index = -1

        for i, rect in enumerate(self._button_rects):
            btn_rect = QRect(rect.x(), rect.y(), self._btn_size, self._btn_size)
            # 检查是否在圆形区域内
            center = btn_rect.center()
            dx = pos.x() - center.x()
            dy = pos.y() - center.y()
            if dx * dx + dy * dy <= (self._btn_size // 2) ** 2:
                self._hover_index = i
                break

        if self._hover_index != old_hover:
            self.setCursor(Qt.PointingHandCursor if self._hover_index >= 0 else Qt.ArrowCursor)
            self.update()

    def mousePressEvent(self, event):
        """点击处理"""
        if event.button() == Qt.LeftButton and self._hover_index >= 0:
            item = self._items[self._hover_index]
            self.close()
            # 延迟执行回调，避免菜单还在显示时执行
            QTimer.singleShot(50, item.callback)
        elif event.button() == Qt.LeftButton:
            # 点击空白处关闭
            self.close()

    def keyPressEvent(self, event):
        """ESC 关闭"""
        if event.key() == Qt.Key_Escape:
            self.close()

    def leaveEvent(self, event):
        """鼠标离开"""
        if self._hover_index >= 0:
            self._hover_index = -1
            self.update()
