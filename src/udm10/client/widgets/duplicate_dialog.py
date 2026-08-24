"""Protected-focus resolution dialog for a duplicate server filename."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from udm10.client.models.upload import ConflictPolicy, UploadItem
from udm10.client.ui.icons import line_icon
from udm10.client.ui.theme import COLORS
from udm10.client.widgets.elided_label import ElidedLabel


class DuplicateDialog(QDialog):
    def __init__(self, item: UploadItem, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Xử lý tệp trùng tên")
        self.setModal(True)
        self.setMinimumWidth(560)
        self.setMaximumWidth(640)
        self.setAccessibleName(f"Xử lý tệp trùng tên {item.name}")
        self._choice: ConflictPolicy | None = None

        icon = QLabel()
        icon.setPixmap(line_icon("warning", COLORS["warning"], 24).pixmap(24, 24))
        icon.setFixedSize(28, 28)
        title = QLabel("Tệp đã tồn tại trên máy chủ")
        title.setObjectName("PageTitle")
        subtitle = ElidedLabel(item.name)
        subtitle.setObjectName("MutedText")
        subtitle.setMinimumWidth(420)

        title_text = QVBoxLayout()
        title_text.setContentsMargins(0, 0, 0, 0)
        title_text.setSpacing(2)
        title_text.addWidget(title)
        title_text.addWidget(subtitle)
        header = QHBoxLayout()
        header.setSpacing(12)
        header.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        header.addLayout(title_text, 1)

        explanation = QLabel("Chọn cách xử lý trước khi tiếp tục tải tệp này.")
        explanation.setObjectName("MutedText")

        self._group = QButtonGroup(self)
        self._radios: list[QRadioButton] = []
        options = [
            (ConflictPolicy.OVERWRITE, "Ghi đè", "Thay thế tệp hiện có bằng tệp mới."),
            (ConflictPolicy.RENAME, "Đổi tên", "Giữ cả hai; máy chủ sẽ tạo một tên an toàn."),
            (ConflictPolicy.SKIP, "Bỏ qua", "Không tải tệp này lên máy chủ."),
        ]
        options_layout = QVBoxLayout()
        options_layout.setSpacing(4)
        for policy, label, description in options:
            radio = QRadioButton(label)
            radio.setProperty("policy", policy.value)
            radio.setAccessibleDescription(description)
            detail = QLabel(description)
            detail.setObjectName("MutedText")
            detail.setContentsMargins(28, 0, 0, 4)
            options_layout.addWidget(radio)
            options_layout.addWidget(detail)
            self._group.addButton(radio)
            self._radios.append(radio)

        self.apply_all = QCheckBox("Áp dụng cho các tệp trùng còn lại")
        self.apply_all.setAccessibleDescription(
            "Dùng cùng lựa chọn cho mọi tệp đang chờ xử lý trùng tên"
        )
        self._cancel = QPushButton("Hủy")
        self._cancel.clicked.connect(self.reject)
        self._continue = QPushButton("Tiếp tục")
        self._continue.setObjectName("PrimaryButton")
        self._continue.setDisabled(True)
        self._continue.clicked.connect(self._accept_choice)
        self._group.buttonToggled.connect(self._on_option_toggled)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self._cancel)
        actions.addWidget(self._continue)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addLayout(header)
        layout.addWidget(explanation)
        layout.addLayout(options_layout)
        layout.addWidget(self.apply_all)
        layout.addSpacing(4)
        layout.addLayout(actions)
        self.setTabOrder(self._radios[0], self._radios[1])
        self.setTabOrder(self._radios[1], self._radios[2])
        self.setTabOrder(self._radios[2], self.apply_all)
        self.setTabOrder(self.apply_all, self._cancel)
        self.setTabOrder(self._cancel, self._continue)
        self._radios[0].setFocus()

    def selected_policy(self) -> ConflictPolicy | None:
        return self._choice

    def apply_to_remaining(self) -> bool:
        return self.apply_all.isChecked()

    def _on_option_toggled(self, button, checked: bool) -> None:
        if not checked:
            return
        self._choice = ConflictPolicy(button.property("policy"))
        destructive = self._choice == ConflictPolicy.OVERWRITE
        self._continue.setObjectName(
            "DangerButton" if destructive else "PrimaryButton"
        )
        self._continue.setText("Ghi đè tệp" if destructive else "Tiếp tục")
        self._continue.setAccessibleDescription(
            "Thay thế vĩnh viễn tệp hiện có trên máy chủ"
            if destructive
            else "Xác nhận cách xử lý tệp trùng tên"
        )
        self._continue.style().unpolish(self._continue)
        self._continue.style().polish(self._continue)
        self._continue.setEnabled(True)

    def _accept_choice(self) -> None:
        if self._choice is not None:
            self.accept()
