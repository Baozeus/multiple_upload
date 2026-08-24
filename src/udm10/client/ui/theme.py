"""UDM_10 visual tokens expressed as a Qt stylesheet."""

from __future__ import annotations


COLORS = {
    "canvas": "#F5F7FA",
    "surface": "#FFFFFF",
    "surface_subtle": "#EEF2F6",
    "text": "#17212B",
    "muted": "#52606D",
    "disabled": "#8994A1",
    "border": "#D6DEE8",
    "border_strong": "#A9B5C3",
    "accent": "#2457D6",
    "accent_hover": "#1D47B2",
    "accent_subtle": "#EAF0FF",
    "focus": "#0B63CE",
    "success": "#18794E",
    "success_subtle": "#E8F5EE",
    "warning": "#8A6100",
    "warning_subtle": "#FFF4CE",
    "error": "#B42318",
    "error_subtle": "#FEECEB",
    "offline": "#475467",
}


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        color: {COLORS['text']};
        font-family: "Segoe UI", "Microsoft YaHei UI", "Noto Sans", Arial, sans-serif;
        font-size: 14px;
    }}
    QMainWindow, QWidget#AppRoot {{ background: {COLORS['canvas']}; }}
    QFrame#TopNavigation {{
        background: {COLORS['surface']};
        border: none;
        border-bottom: 1px solid {COLORS['border']};
    }}
    QToolButton#BrandButton {{
        color: {COLORS['text']};
        border: none;
        background: transparent;
        font-size: 15px;
        font-weight: 700;
        min-height: 40px;
        padding: 0 8px;
    }}
    QToolButton#NavButton {{
        color: {COLORS['muted']};
        border: none;
        border-bottom: 2px solid transparent;
        background: transparent;
        font-weight: 600;
        min-height: 52px;
        padding: 0 16px;
    }}
    QToolButton#NavButton:hover {{ background: {COLORS['surface_subtle']}; color: {COLORS['text']}; }}
    QToolButton#NavButton:focus {{ border: 2px solid {COLORS['focus']}; border-bottom: 2px solid {COLORS['focus']}; }}
    QToolButton#NavButton[active="true"] {{
        color: {COLORS['accent']};
        border-bottom: 2px solid {COLORS['accent']};
        background: {COLORS['surface']};
    }}
    QLabel#DisplayTitle {{ font-size: 28px; font-weight: 700; color: {COLORS['text']}; }}
    QLabel#PageTitle {{ font-size: 22px; font-weight: 700; color: {COLORS['text']}; }}
    QLabel#SectionTitle {{ font-size: 16px; font-weight: 700; color: {COLORS['text']}; }}
    QLabel#MutedText {{ color: {COLORS['muted']}; }}
    QLabel#Caption {{ color: {COLORS['muted']}; font-size: 12px; font-weight: 600; }}
    QFrame#Surface {{
        background: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
    }}
    QPushButton {{
        min-height: 38px;
        padding: 0 16px;
        border: 1px solid {COLORS['border_strong']};
        border-radius: 6px;
        background: {COLORS['surface']};
        color: {COLORS['text']};
        font-weight: 600;
    }}
    QPushButton:hover {{ background: {COLORS['surface_subtle']}; border-color: {COLORS['muted']}; }}
    QPushButton:pressed {{ background: {COLORS['border']}; }}
    QPushButton:focus {{ border: 2px solid {COLORS['focus']}; padding: 0 15px; }}
    QPushButton:disabled {{ color: {COLORS['disabled']}; background: {COLORS['surface_subtle']}; border-color: {COLORS['border']}; }}
    QPushButton#PrimaryButton {{
        background: {COLORS['accent']};
        color: white;
        border: 2px solid {COLORS['accent']};
    }}
    QPushButton#PrimaryButton:hover {{ background: {COLORS['accent_hover']}; border-color: {COLORS['accent_hover']}; }}
    QPushButton#PrimaryButton:pressed {{ background: #183C95; border-color: #183C95; }}
    QPushButton#PrimaryButton:focus {{ border: 2px solid #9CC4FF; }}
    QPushButton#PrimaryButton:disabled {{
        color: {COLORS['disabled']};
        background: {COLORS['surface_subtle']};
        border-color: {COLORS['border']};
    }}
    QPushButton#DangerButton {{ color: {COLORS['error']}; border-color: #E9A7A1; }}
    QPushButton#DangerButton:hover {{ background: {COLORS['error_subtle']}; border-color: {COLORS['error']}; }}
    QToolButton#IconButton {{
        min-width: 38px;
        min-height: 38px;
        max-width: 38px;
        max-height: 38px;
        border: 1px solid transparent;
        border-radius: 6px;
        background: transparent;
    }}
    QToolButton#IconButton:hover {{ background: {COLORS['surface_subtle']}; border-color: {COLORS['border']}; }}
    QToolButton#IconButton:focus {{ border: 2px solid {COLORS['focus']}; }}
    QLineEdit, QComboBox {{
        min-height: 38px;
        border: 1px solid {COLORS['border_strong']};
        border-radius: 6px;
        background: {COLORS['surface']};
        padding: 0 12px;
        selection-background-color: {COLORS['accent']};
    }}
    QLineEdit:focus, QComboBox:focus {{ border: 2px solid {COLORS['focus']}; padding: 0 11px; }}
    QLineEdit::placeholder {{ color: {COLORS['disabled']}; }}
    QComboBox::drop-down {{ width: 28px; border: none; }}
    QComboBox QAbstractItemView {{
        background: {COLORS['surface']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['accent_subtle']};
        selection-color: {COLORS['text']};
        outline: none;
    }}
    QFrame#DropZone {{
        background: {COLORS['surface']};
        border: 1px dashed {COLORS['border_strong']};
        border-radius: 8px;
    }}
    QFrame#DropZone[dragActive="true"] {{
        background: {COLORS['accent_subtle']};
        border: 2px solid {COLORS['accent']};
    }}
    QFrame#DropZone:focus {{ border: 2px solid {COLORS['focus']}; }}
    QFrame#SummaryStrip {{ background: {COLORS['surface']}; border: none; border-bottom: 1px solid {COLORS['border']}; }}
    QFrame#SummaryDivider {{ background: {COLORS['border']}; min-width: 1px; max-width: 1px; }}
    QLabel#MetricValue {{ font-size: 20px; font-weight: 700; }}
    QFrame#UploadRow {{ background: {COLORS['surface']}; border: none; border-bottom: 1px solid {COLORS['border']}; }}
    QFrame#UploadRow:hover {{ background: #FAFBFC; }}
    QFrame#UploadRow[rowState="failed"] {{ background: #FFFAF9; }}
    QFrame#UploadRow[rowState="conflict"] {{ background: #FFFCF1; }}
    QProgressBar {{
        min-height: 7px;
        max-height: 7px;
        border: none;
        border-radius: 3px;
        background: {COLORS['border']};
        text-align: center;
    }}
    QProgressBar::chunk {{ background: {COLORS['accent']}; border-radius: 3px; }}
    QFrame#ErrorMessage {{ background: {COLORS['error_subtle']}; border: none; border-radius: 6px; }}
    QFrame#WarningMessage {{ background: {COLORS['warning_subtle']}; border: none; border-radius: 6px; }}
    QFrame#OfflineBanner {{ background: #EEF1F5; border: none; border-bottom: 1px solid {COLORS['border']}; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: {COLORS['surface']}; }}
    QTableView {{
        background: {COLORS['surface']};
        alternate-background-color: #FAFBFC;
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        gridline-color: {COLORS['border']};
        selection-background-color: {COLORS['accent_subtle']};
        selection-color: {COLORS['text']};
        outline: none;
    }}
    QTableView::item {{ padding: 8px 12px; border-bottom: 1px solid {COLORS['border']}; }}
    QTableView::item:focus {{ border: 2px solid {COLORS['focus']}; }}
    QHeaderView::section {{
        background: {COLORS['surface_subtle']};
        color: {COLORS['muted']};
        border: none;
        border-bottom: 1px solid {COLORS['border']};
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 700;
    }}
    QDialog {{ background: {COLORS['surface']}; }}
    QRadioButton {{ spacing: 10px; min-height: 38px; }}
    QRadioButton:focus {{ color: {COLORS['accent']}; }}
    QCheckBox {{ spacing: 8px; min-height: 36px; }}
    QToolTip {{ background: {COLORS['text']}; color: white; border: none; padding: 6px 8px; }}
    """
