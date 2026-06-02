"""系统托盘图标模块"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush, QRadialGradient, QPainterPath
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication


def _create_tray_icon_pixmap() -> QPixmap:
    """生成桌面助手托盘图标（可爱的小精灵风格）。"""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 背景圆形（柔和渐变）
    gradient = QRadialGradient(32, 28, 30)
    gradient.setColorAt(0, QColor("#E8DEF8"))
    gradient.setColorAt(1, QColor("#B088C0"))
    
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(gradient))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # 外圈描边
    painter.setPen(QPen(QColor("#8B6FAE"), 2))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # 眼睛（两个小圆点）
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#6B4E8D")))
    painter.drawEllipse(22, 24, 6, 6)  # 左眼
    painter.drawEllipse(36, 24, 6, 6)  # 右眼

    # 眼睛高光
    painter.setBrush(QBrush(QColor("#FFFFFF")))
    painter.drawEllipse(24, 25, 2, 2)  # 左眼高光
    painter.drawEllipse(38, 25, 2, 2)  # 右眼高光

    # 嘴巴（小弧线）
    painter.setPen(QPen(QColor("#6B4E8D"), 1.5))
    painter.setBrush(Qt.NoBrush)
    mouth = QPainterPath()
    mouth.moveTo(28, 36)
    mouth.quadTo(32, 40, 36, 36)
    painter.drawPath(mouth)

    # 腮红（粉色小圆）
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#FFB6C1")))
    painter.drawEllipse(16, 32, 6, 4)  # 左腮红
    painter.drawEllipse(42, 32, 6, 4)  # 右腮红

    # 头顶小星星装饰
    painter.setPen(QPen(QColor("#FFD700"), 1))
    painter.setBrush(QBrush(QColor("#FFD700")))
    star = QPainterPath()
    star.moveTo(32, 6)
    star.lineTo(34, 12)
    star.lineTo(40, 12)
    star.lineTo(35, 16)
    star.lineTo(37, 22)
    star.lineTo(32, 18)
    star.lineTo(27, 22)
    star.lineTo(29, 16)
    star.lineTo(24, 12)
    star.lineTo(30, 12)
    star.closeSubpath()
    painter.drawPath(star)

    painter.end()
    return pixmap


class TrayIcon(QSystemTrayIcon):
    """系统托盘图标。"""

    show_pet_clicked = pyqtSignal()   # 显示小赫
    restart_clicked = pyqtSignal()    # 重启应用

    def __init__(self, parent=None):
        super().__init__(parent)

        pixmap = _create_tray_icon_pixmap()
        self.setIcon(QIcon(pixmap))
        self.setToolTip("Hermes Desktop Pet")

        self._menu = QMenu()
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #FFF;
                border: 1px solid #D0C0E0;
                border-radius: 6px;
                padding: 4px;
                font-family: 'Microsoft YaHei';
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #E8DEF8;
            }
        """)

        # 显示小赫
        self._show_action = QAction("显示小赫", self)
        self._show_action.triggered.connect(self.show_pet_clicked.emit)
        self._menu.addAction(self._show_action)

        self._menu.addSeparator()

        # 显示/隐藏聊天
        self._toggle_action = QAction("显示/隐藏聊天", self)
        self._menu.addAction(self._toggle_action)

        self._menu.addSeparator()

        # 重启
        self._restart_action = QAction("重启", self)
        self._restart_action.triggered.connect(self.restart_clicked.emit)
        self._menu.addAction(self._restart_action)

        # 退出
        self._quit_action = QAction("退出", self)
        self._quit_action.triggered.connect(QApplication.quit)
        self._menu.addAction(self._quit_action)

        self.setContextMenu(self._menu)

        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_pet_clicked.emit()

    def connect_toggle(self, callback):
        self._toggle_action.triggered.connect(callback)
