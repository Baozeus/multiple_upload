"""Visual tokens and application stylesheet for the Compact Ledger UI."""

APP_STYLESHEET = """
QWidget {
    color: #273142;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow, QWidget#appRoot, QWidget#contentPage { background: #F7F8FA; }
QFrame#navRail {
    background: #FFFFFF;
    border-right: 1px solid #E3E7EC;
}
QFrame#brandBlock { background: transparent; border: none; }
QLabel#brandName { color: #172033; font-size: 15px; font-weight: 700; }
QLabel#brandMeta {
    color: #657184;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.4px;
}
QPushButton#navButton {
    min-height: 44px;
    padding: 0 13px;
    border: none;
    border-left: 1px solid transparent;
    border-radius: 7px;
    background: transparent;
    color: #435064;
    text-align: left;
    font-weight: 600;
}
QPushButton#navButton:hover { background: #F4F7FB; color: #172033; }
QPushButton#navButton:checked {
    background: #EAF2FE;
    color: #0B62CE;
    border-left-color: #1769E0;
}
QLabel#pageTitle { color: #141B26; font-size: 24px; font-weight: 700; }
QLabel#pageSubtitle, QLabel#muted { color: #5F6B7A; font-size: 13px; }
QLabel#sectionTitle { color: #172033; font-size: 16px; font-weight: 700; }
QLabel#sectionMeta { color: #5F6B7A; font-size: 12px; }
QFrame#dropZone {
    background: #FFFFFF;
    border: 1px dashed #8FA7C2;
    border-radius: 10px;
}
QFrame#dropZone:hover { border-color: #1769E0; background: #FBFDFF; }
QFrame#dropZone:focus { border: 2px solid #1769E0; }
QFrame#dropZone[dragActive="true"] {
    background: #EAF2FE;
    border: 2px dashed #1769E0;
}
QFrame#dropIconWrap { background: #EAF2FE; border: none; border-radius: 10px; }
QLabel#dropTitle { color: #172033; font-size: 16px; font-weight: 700; }
QPushButton {
    min-height: 36px;
    padding: 0 13px;
    border: 1px solid #D4DAE2;
    border-radius: 8px;
    background: #FFFFFF;
    color: #273142;
    font-weight: 600;
}
QPushButton:hover { background: #F4F7FB; border-color: #AEB8C5; }
QPushButton:pressed { background: #E9EDF2; }
QPushButton:focus { border: 2px solid #1769E0; }
QPushButton:disabled { color: #8A96A7; background: #F0F2F5; border-color: #E1E5EA; }
QPushButton#primaryButton {
    color: #FFFFFF;
    background: #1769E0;
    border-color: #1769E0;
    min-width: 112px;
}
QPushButton#primaryButton:hover { background: #0B5CC4; border-color: #0B5CC4; }
QPushButton#dangerButton { color: #B3261E; }
QPushButton#quietButton { background: transparent; border-color: transparent; color: #1769E0; }
QPushButton#quietButton:hover { background: #EAF2FE; }
QPushButton#rowActionButton {
    min-height: 30px;
    padding: 0 8px;
    background: transparent;
    border-color: transparent;
    color: #1769E0;
    font-size: 12px;
    text-align: left;
}
QPushButton#rowActionButton:hover { background: #EAF2FE; }
QFrame#statusLedger {
    background: transparent;
    border-top: 1px solid #DFE4EA;
    border-bottom: 1px solid #DFE4EA;
}
QFrame#metricDivider { background: #DFE4EA; border: none; }
QLabel#metricLabel { color: #657184; font-size: 11px; }
QLabel#metricValue { color: #273142; font-size: 18px; font-weight: 700; }
QLabel#metricValue[tone="uploading"] { color: #1769E0; }
QLabel#metricValue[tone="waiting"] { color: #A46200; }
QLabel#metricValue[tone="completed"] { color: #137A49; }
QLabel#metricValue[tone="error"] { color: #B3261E; }
QFrame#tablePanel {
    background: #FFFFFF;
    border: 1px solid #DFE4EA;
    border-radius: 10px;
}
QFrame#tableHeader {
    background: #F8F9FB;
    border-top: 1px solid #E2E6EB;
    border-bottom: 1px solid #E2E6EB;
}
QLabel#columnLabel { color: #566274; font-size: 11px; font-weight: 650; }
QFrame#fileRow, QFrame#historyRow {
    background: #FFFFFF;
    border: none;
    border-bottom: 1px solid #EDF0F3;
}
QFrame#fileRow:hover, QFrame#historyRow:hover { background: #FAFCFF; }
QWidget#tableBody { background: #FFFFFF; }
QLabel#fileName { color: #202A39; font-weight: 600; }
QLabel#rowDetail { color: #657184; font-size: 11px; }
QLabel#dataCell, QLabel#percentCell { color: #435064; font-size: 12px; }
QLabel#percentCell { font-weight: 650; }
QProgressBar {
    min-height: 7px;
    max-height: 7px;
    background: #E9EDF2;
    border: none;
    border-radius: 3px;
}
QProgressBar::chunk { background: #1769E0; border-radius: 3px; }
QProgressBar[progressState="completed"]::chunk { background: #188038; }
QProgressBar[progressState="error"]::chunk { background: #D93025; }
QProgressBar[progressState="waiting"]::chunk { background: #C57B08; }
QFrame#statusBadge {
    border-radius: 7px;
}
QLabel#statusText {
    background: transparent;
    font-size: 11px;
    font-weight: 700;
}
QFrame#statusBadge[status="waiting"] { color: #945A00; background: #FFF4DE; }
QFrame#statusBadge[status="uploading"] { color: #0B62CE; background: #EAF2FE; }
QFrame#statusBadge[status="completed"] { color: #137A49; background: #E6F4EC; }
QFrame#statusBadge[status="error"] { color: #B3261E; background: #FDECEA; }
QFrame#emptyState { background: #FFFFFF; border: none; }
QLabel#emptyTitle { color: #273142; font-size: 15px; font-weight: 650; }
QFrame#infoStrip { background: #F0F5FB; border: none; border-radius: 8px; }
QLabel#infoText { color: #435B73; font-size: 12px; }
QLineEdit, QComboBox {
    min-height: 36px;
    padding: 0 11px;
    background: #FFFFFF;
    border: 1px solid #D4DAE2;
    border-radius: 8px;
    selection-background-color: #CFE1FB;
}
QLineEdit:focus, QComboBox:focus { border: 2px solid #1769E0; }
QLineEdit::placeholder { color: #7B8796; }
QComboBox::drop-down { border: none; width: 28px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { min-height: 34px; background: #C3CBD5; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background: #9DA8B6; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QStatusBar { background: #FFFFFF; color: #566274; border-top: 1px solid #E3E7EC; }
QToolTip {
    color: #FFFFFF;
    background: #273142;
    border: 1px solid #273142;
    padding: 5px 7px;
}
"""
