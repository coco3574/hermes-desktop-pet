"""人格添加/编辑对话框"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QPushButton, QLabel,
    QFileDialog, QColorDialog, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from .personas import Persona, persona_manager


class PersonaDialog(QDialog):
    """添加/编辑人格对话框"""
    
    def __init__(self, parent=None, persona: Persona = None):
        super().__init__(parent)
        self.persona = persona  # 编辑模式时传入
        self.is_edit = persona is not None
        
        self.setWindowTitle("编辑人格" if self.is_edit else "添加新人格")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
            }
            QLabel {
                font-family: 'Microsoft YaHei';
                font-size: 13px;
            }
            QLineEdit, QTextEdit, QComboBox {
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                padding: 8px;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                background-color: white;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #B088C0;
            }
            QPushButton {
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                padding: 8px 20px;
                border-radius: 6px;
                border: none;
            }
        """)
        
        self._setup_ui()
        
        # 编辑模式：填充现有数据
        if self.is_edit:
            self._fill_data()
    
    def _on_tts_provider_changed(self, text: str):
        """TTS 提供商改变时更新音色选项"""
        self._update_voice_options(text)
        # 更新模型输入框的占位符提示
        if text == "edge-tts":
            self.tts_model_input.setPlaceholderText("edge-tts 无需模型名称，留空即可")
        elif text == "xiaomi":
            self.tts_model_input.setPlaceholderText("如: tts-1")
        elif text == "openai":
            self.tts_model_input.setPlaceholderText("如: tts-1, tts-1-hd")
        else:
            self.tts_model_input.setPlaceholderText("如: tts-1（xiaomi/openai 专用，edge-tts 留空）")

    def _update_voice_options(self, provider: str):
        """根据 TTS 提供商更新音色下拉框选项"""
        self.tts_voice_combo.clear()
        voice_options = {
            "(使用全局配置)": [],
            "edge-tts": [
                "zh-CN-XiaoxiaoNeural",
                "zh-CN-YunxiNeural",
                "zh-CN-YunyangNeural",
                "zh-CN-XiaoyiNeural",
                "zh-CN-XiaohanNeural",
                "en-US-AriaNeural",
                "en-US-GuyNeural",
            ],
            "xiaomi": [
                "Chloe",
                "alloy",
                "echo",
                "fable",
                "onyx",
                "nova",
                "shimmer",
            ],
            "openai": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        }
        options = voice_options.get(provider, [])
        if options:
            self.tts_voice_combo.addItems(options)
        else:
            # "(使用全局配置)" 或未知提供商，允许手动输入
            self.tts_voice_combo.setPlaceholderText("输入音色名称或留空使用全局配置")
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 表单
        form = QFormLayout()
        
        # 人格ID（编辑时不可改）
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("英文标识，如 xiaohe、stock-analyst")
        if self.is_edit:
            self.id_input.setEnabled(False)
        form.addRow("人格 ID:", self.id_input)
        
        # 显示名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("如：小赫、股票分析师")
        form.addRow("显示名称:", self.name_input)
        
        # API Endpoint
        self.endpoint_input = QLineEdit()
        self.endpoint_input.setPlaceholderText("http://localhost:8643/v1/chat/completions")
        form.addRow("API Endpoint:", self.endpoint_input)
        
        # API Key
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("desktop-pet-key-2026")
        form.addRow("API Key:", self.key_input)
        
        # Model Name
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("对应 Hermes profile 名称")
        form.addRow("Model Name:", self.model_input)
        
        # 形象选择
        skin_layout = QHBoxLayout()
        self.skin_input = QLineEdit()
        self.skin_input.setPlaceholderText("angel_sprite.png")
        self.skin_input.setReadOnly(True)
        skin_layout.addWidget(self.skin_input)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8DEF8;
                color: #2D2D2D;
            }
            QPushButton:hover {
                background-color: #D0C0E0;
            }
        """)
        browse_btn.clicked.connect(self._browse_skin)
        skin_layout.addWidget(browse_btn)
        form.addRow("形象图片:", skin_layout)
        
        # 主题色
        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setStyleSheet("background-color: #B088C0; border: 1px solid #999; border-radius: 4px;")
        color_layout.addWidget(self.color_preview)
        
        self.color_input = QLineEdit("#B088C0")
        self.color_input.textChanged.connect(self._update_color_preview)
        color_layout.addWidget(self.color_input)
        
        color_btn = QPushButton("选择...")
        color_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8DEF8;
                color: #2D2D2D;
            }
            QPushButton:hover {
                background-color: #D0C0E0;
            }
        """)
        color_btn.clicked.connect(self._pick_color)
        color_layout.addWidget(color_btn)
        form.addRow("主题色:", color_layout)
        
        # 描述
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("这个人格是做什么的...")
        form.addRow("描述:", self.desc_input)
        
        # System Prompt
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("客户端补充的 system prompt（可选）")
        self.prompt_input.setMaximumHeight(100)
        form.addRow("System Prompt:", self.prompt_input)
        
        # === 语音配置 ===
        voice_label = QLabel("🎤 语音配置")
        voice_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #666; margin-top: 10px;")
        form.addRow(voice_label)

        # TTS 提供商
        self.tts_provider_combo = QComboBox()
        self.tts_provider_combo.addItems(["(使用全局配置)", "edge-tts", "xiaomi", "openai"])
        self.tts_provider_combo.currentTextChanged.connect(self._on_tts_provider_changed)
        form.addRow("TTS 提供商:", self.tts_provider_combo)

        # TTS 模型名称（xiaomi/openai 用）
        self.tts_model_input = QLineEdit()
        self.tts_model_input.setPlaceholderText("如: tts-1（xiaomi/openai 专用，edge-tts 留空）")
        form.addRow("TTS 模型:", self.tts_model_input)

        # 音色（下拉框）
        self.tts_voice_combo = QComboBox()
        self.tts_voice_combo.setEditable(True)  # 允许手动输入自定义音色
        self._update_voice_options("(使用全局配置)")
        form.addRow("音色:", self.tts_voice_combo)

        # TTS API Key
        self.tts_api_key_input = QLineEdit()
        self.tts_api_key_input.setPlaceholderText("可选，覆盖全局 API Key")
        self.tts_api_key_input.setEchoMode(QLineEdit.Password)
        form.addRow("TTS API Key:", self.tts_api_key_input)

        # TTS 端点
        self.tts_endpoint_input = QLineEdit()
        self.tts_endpoint_input.setPlaceholderText("可选，如: https://api.openai.com/v1/audio/speech")
        form.addRow("TTS 端点:", self.tts_endpoint_input)
        
        layout.addLayout(form)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #B088C0;
                color: white;
            }
            QPushButton:hover {
                background-color: #9868A8;
            }
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
    
    def _fill_data(self):
        """编辑模式：填充现有数据"""
        if not self.persona:
            return
        
        self.id_input.setText(self.persona.id)
        self.name_input.setText(self.persona.name)
        self.endpoint_input.setText(self.persona.api_endpoint)
        self.key_input.setText(self.persona.api_key)
        self.model_input.setText(self.persona.model_name)
        self.skin_input.setText(self.persona.skin)
        self.color_input.setText(self.persona.theme_color)
        self.desc_input.setText(self.persona.description)
        self.prompt_input.setPlainText(self.persona.system_prompt)
        
        # 语音配置
        if self.persona.tts_provider:
            index = self.tts_provider_combo.findText(self.persona.tts_provider)
            if index >= 0:
                self.tts_provider_combo.setCurrentIndex(index)
        self.tts_model_input.setText(self.persona.tts_model)
        # 设置音色下拉框的值
        if self.persona.tts_voice:
            index = self.tts_voice_combo.findText(self.persona.tts_voice)
            if index >= 0:
                self.tts_voice_combo.setCurrentIndex(index)
            else:
                self.tts_voice_combo.setEditText(self.persona.tts_voice)
        self.tts_api_key_input.setText(self.persona.tts_api_key)
        self.tts_endpoint_input.setText(self.persona.tts_endpoint)
    
    def _browse_skin(self):
        """浏览选择形象图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择形象图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*.*)"
        )
        if file_path:
            # 只保存文件名，因为图片应该在 assets 目录
            import os
            filename = os.path.basename(file_path)
            self.skin_input.setText(filename)
    
    def _pick_color(self):
        """选择主题色"""
        current = QColor(self.color_input.text())
        color = QColorDialog.getColor(current, self, "选择主题色")
        if color.isValid():
            self.color_input.setText(color.name())
    
    def _update_color_preview(self, text: str):
        """更新颜色预览"""
        try:
            QColor(text).isValid()
            self.color_preview.setStyleSheet(f"background-color: {text}; border: 1px solid #999; border-radius: 4px;")
        except:
            pass
    
    def _save(self):
        """保存人格配置"""
        # 验证必填项
        id_text = self.id_input.text().strip()
        name_text = self.name_input.text().strip()
        endpoint_text = self.endpoint_input.text().strip()
        model_text = self.model_input.text().strip()
        
        if not all([id_text, name_text, endpoint_text, model_text]):
            QMessageBox.warning(self, "提示", "请填写所有必填项（ID、名称、API Endpoint、Model）")
            return
        
        # 验证ID格式（只能英文、数字、连字符）
        import re
        if not re.match(r'^[a-z0-9-]+$', id_text):
            QMessageBox.warning(self, "提示", "人格 ID 只能包含小写字母、数字和连字符")
            return
        
        # 创建 Persona 对象
        # TTS 提供商：如果选择"(使用全局配置)"则设为空字符串
        tts_provider = self.tts_provider_combo.currentText()
        if tts_provider == "(使用全局配置)":
            tts_provider = ""

        persona = Persona(
            id=id_text,
            name=name_text,
            api_endpoint=endpoint_text,
            api_key=self.key_input.text().strip(),
            model_name=model_text,
            skin=self.skin_input.text().strip() or "angel_sprite.png",
            system_prompt=self.prompt_input.toPlainText().strip(),
            theme_color=self.color_input.text().strip() or "#B088C0",
            description=self.desc_input.text().strip(),
            tts_provider=tts_provider,
            tts_model=self.tts_model_input.text().strip(),
            tts_voice=self.tts_voice_combo.currentText().strip(),
            tts_api_key=self.tts_api_key_input.text().strip(),
            tts_endpoint=self.tts_endpoint_input.text().strip(),
        )
        
        # 保存
        if self.is_edit:
            success = persona_manager.update(persona)
        else:
            success = persona_manager.add(persona)
        
        if success:
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "保存失败，可能是 ID 已存在")


class PersonaListDialog(QDialog):
    """人格列表管理对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("人格管理")
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #FAFAFA;
            }
            QListWidget {
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                border: 1px solid #D0D0D0;
                border-radius: 6px;
                background-color: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #EEE;
            }
            QListWidget::item:selected {
                background-color: #E8DEF8;
            }
            QListWidget::item:hover {
                background-color: #F0E6FF;
            }
        """)
        
        self._setup_ui()
        self._refresh_list()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("人格列表")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        # 列表
        from PyQt5.QtWidgets import QListWidget
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._edit_persona)
        layout.addWidget(self.list_widget)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("添加新人格")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #B088C0;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #9868A8;
            }
        """)
        add_btn.clicked.connect(self._add_persona)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("编辑")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8DEF8;
                color: #2D2D2D;
            }
            QPushButton:hover {
                background-color: #D0C0E0;
            }
        """)
        edit_btn.clicked.connect(self._edit_persona)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFE0E0;
                color: #CC3333;
            }
            QPushButton:hover {
                background-color: #FFD0D0;
            }
        """)
        delete_btn.clicked.connect(self._delete_persona)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _refresh_list(self):
        """刷新人格列表"""
        self.list_widget.clear()
        current = persona_manager.get_current()
        
        for persona in persona_manager.get_all():
            is_current = current and persona.id == current.id
            prefix = "👉 " if is_current else "    "
            item_text = f"{prefix}{persona.name} ({persona.id}) - {persona.model_name}"
            self.list_widget.addItem(item_text)
    
    def _add_persona(self):
        """添加新人格"""
        dialog = PersonaDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._refresh_list()
    
    def _edit_persona(self):
        """编辑人格"""
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个人格")
            return
        
        # 获取人格ID
        text = current_item.text()
        id_match = text.split("(")[1].split(")")[0] if "(" in text else None
        
        if not id_match:
            return
        
        persona = persona_manager.personas.get(id_match)
        if not persona:
            return
        
        dialog = PersonaDialog(self, persona)
        if dialog.exec_() == QDialog.Accepted:
            self._refresh_list()
    
    def _delete_persona(self):
        """删除人格"""
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个人格")
            return
        
        text = current_item.text()
        id_match = text.split("(")[1].split(")")[0] if "(" in text else None
        
        if not id_match:
            return
        
        persona = persona_manager.personas.get(id_match)
        if not persona:
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除人格「{persona.name}」吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if persona_manager.delete(id_match):
                self._refresh_list()
            else:
                QMessageBox.warning(self, "错误", "删除失败，不能删除当前使用的人格")
