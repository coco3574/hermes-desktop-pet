"""系统托盘图标模块"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen, QBrush
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication


def _create_tray_icon_pixmap() -> QPixmap:
    """生成一个简单的托盘图标（16x16 紫色圆形 + H 字母）。"""
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor("#B088C0")))
    painter.drawEllipse(2, 2, size - 4, size - 4)

    painter.setPen(QPen(QColor("#FFFFFF"), 2))
    font = QFont("Arial", 16, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "H")

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
