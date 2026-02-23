"""Main GUI application for von Frey Up-Down Analysis Tool.

Implements the left sidebar + main panel layout with 6 steps:
1. Data Loading
2. Metadata & Groups
3. Appearance
4. Plot Preview
5. Statistics
6. Export
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .data_input import DataInputPanel
from .export_panel import ExportPanel, StatsPanel
from .group_config import GroupConfigPanel
from .plot_config import AppearancePanel, PreviewPanel
from .state import AnalysisState


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation."""

    def __init__(self) -> None:
        super().__init__()
        self.state = AnalysisState()
        self.setWindowTitle("Von Frey Up-Down Analysis Tool")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        self._init_menu()
        self._init_ui()
        self._connect_signals()

        self.statusBar().showMessage("Ready. Load your data files to begin.")

    def _init_menu(self) -> None:
        """Create the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        save_session = QAction("Save Session...", self)
        save_session.setShortcut(QKeySequence("Ctrl+S"))
        save_session.triggered.connect(self._save_session)
        file_menu.addAction(save_session)

        load_session = QAction("Load Session...", self)
        load_session.setShortcut(QKeySequence("Ctrl+O"))
        load_session.triggered.connect(self._load_session)
        file_menu.addAction(load_session)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _init_ui(self) -> None:
        """Build the sidebar + stacked main panel layout."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ── Sidebar ──────────────────────────────────────────────────────
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(160)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background-color: #f0f0f0;
                border: none;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)

        steps = [
            "1. Data",
            "2. Groups",
            "3. Appearance",
            "4. Preview",
            "5. Statistics",
            "6. Export",
        ]
        for step in steps:
            item = QListWidgetItem(step)
            item.setSizeHint(QSize(140, 45))
            self.sidebar.addItem(item)

        self.sidebar.currentRowChanged.connect(self._on_step_changed)
        main_layout.addWidget(self.sidebar)

        # ── Main panel (stacked widget) ──────────────────────────────────
        self.stack = QStackedWidget()

        self.data_panel = DataInputPanel(self.state)
        self.group_panel = GroupConfigPanel(self.state)
        self.appearance_panel = AppearancePanel(self.state)
        self.preview_panel = PreviewPanel(self.state)
        self.stats_panel = StatsPanel(self.state)
        self.export_panel = ExportPanel(self.state)

        self.stack.addWidget(self.data_panel)      # index 0
        self.stack.addWidget(self.group_panel)      # index 1
        self.stack.addWidget(self.appearance_panel)  # index 2
        self.stack.addWidget(self.preview_panel)     # index 3
        self.stack.addWidget(self.stats_panel)       # index 4
        self.stack.addWidget(self.export_panel)      # index 5

        main_layout.addWidget(self.stack, stretch=1)

        # Set export panel's figure callback
        self.export_panel.set_figure_callback(self.preview_panel.get_figure)

        # Start on step 1
        self.sidebar.setCurrentRow(0)

    def _connect_signals(self) -> None:
        """Connect inter-panel signals."""
        self.data_panel.data_ready.connect(self._on_data_ready)
        self.group_panel.config_ready.connect(self._on_group_config_ready)
        self.appearance_panel.settings_changed.connect(self._on_appearance_changed)
        self.stats_panel.stats_done.connect(self._on_stats_done)

    def _on_step_changed(self, index: int) -> None:
        """Handle sidebar step navigation."""
        self.stack.setCurrentIndex(index)

        # Refresh panels when entering them
        if index == 1:
            self.group_panel.refresh()
        elif index == 2:
            self.group_panel.get_config()
            self.appearance_panel.refresh()
        elif index == 3:
            self.appearance_panel.get_config()
            self.preview_panel.regenerate_plot()
        elif index == 4:
            self.stats_panel.refresh()
        elif index == 5:
            pass  # export panel doesn't need refresh

    def _on_data_ready(self) -> None:
        """Called when thresholds are computed successfully."""
        self.statusBar().showMessage("Thresholds computed. Proceed to Groups configuration.")
        # Auto-advance to step 2
        self.sidebar.setCurrentRow(1)
        self.group_panel.refresh()

    def _on_group_config_ready(self) -> None:
        """Called when group configuration is done."""
        self.statusBar().showMessage("Groups configured. Set up plot appearance.")

    def _on_appearance_changed(self) -> None:
        """Called when appearance settings change."""
        self.appearance_panel.get_config()

    def _on_stats_done(self) -> None:
        """Called when statistical analysis completes."""
        self.statusBar().showMessage("Statistical analysis complete. Preview updated.")
        # Refresh preview with stats annotations
        self.preview_panel.regenerate_plot()

    def _save_session(self) -> None:
        """Save the current session to a JSON file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", "", "JSON Files (*.json);;All Files (*)"
        )
        if path:
            try:
                self.state.save_session(path)
                self.statusBar().showMessage(f"Session saved to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))

    def _load_session(self) -> None:
        """Load a session from a JSON file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Session", "", "JSON Files (*.json);;All Files (*)"
        )
        if path:
            try:
                self.state = AnalysisState.load_session(path)
                # Reinitialize panels with new state
                self.data_panel.state = self.state
                self.group_panel.state = self.state
                self.appearance_panel.state = self.state
                self.preview_panel.state = self.state
                self.stats_panel.state = self.state
                self.export_panel.state = self.state
                self.statusBar().showMessage(f"Session loaded from {path}")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))


def main() -> None:
    """Launch the GUI application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
