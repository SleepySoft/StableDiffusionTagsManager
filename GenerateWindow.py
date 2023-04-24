import sys
import time

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QDataStream
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDialog, QPushButton, \
    QDialogButtonBox, QCheckBox, QMessageBox, QMenu, QAction

from defines import ANALYSIS_README, PRESET_TAG_PATH, ANALYSIS_SHOW_COLUMNS
from df_utility import *
from TagManager import *
from app_utility import *
from ui_utility import CustomTableWidget, DraggableTree, DataFrameRowEditDialog


class GenerateWindow(QMainWindow):
    def __init__(self, tag_manager: TagManager):
        super().__init__()

        self.tag_manager = tag_manager

        # Create the root layout as a horizontal layout
        root_layout = QHBoxLayout()

        # Create the left group view named "Group" that wraps a DraggableTree
        group_view = QGroupBox("Group")
        group_view_layout = QVBoxLayout()
        draggable_tree = DraggableTree(self.tag_manager.get_database(), self.on_edit_done, parent=self)
        group_view_layout.addWidget(draggable_tree)
        group_view.setLayout(group_view_layout)
        root_layout.addWidget(group_view, 30)

        # Create the center group view named "Tags" that wraps a CustomTableWidget
        tags_view = QGroupBox("Tags")
        tags_view_layout = QVBoxLayout()
        custom_table_widget = CustomTableWidget()
        tags_view_layout.addWidget(custom_table_widget)
        tags_view.setLayout(tags_view_layout)
        root_layout.addWidget(tags_view, 40)

        # Create the right vertical layout
        right_layout = QVBoxLayout()

        # Create the top group view named "Filter"
        filter_view = QGroupBox("Filter")
        filter_view_layout = QVBoxLayout()
        filter_view.setLayout(filter_view_layout)
        right_layout.addWidget(filter_view, 20)

        # Create the group view named "Positive" that wraps a multiple line text editor
        positive_view = QGroupBox("Positive")
        positive_view_layout = QVBoxLayout()
        positive_text_editor = QPlainTextEdit()
        positive_view_layout.addWidget(positive_text_editor)
        positive_view.setLayout(positive_view_layout)
        right_layout.addWidget(positive_view, 50)

        # Create the group view named "Negative" that wraps a multiple line text editor
        negative_view = QGroupBox("Negative")
        negative_view_layout = QVBoxLayout()
        negative_text_editor = QPlainTextEdit()
        negative_view_layout.addWidget(negative_text_editor)
        negative_view.setLayout(negative_view_layout)
        right_layout.addWidget(negative_view, 30)

        # Set the weight of the right layout to 40%
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        root_layout.addWidget(right_widget, 40)

        # Set the root layout
        root_widget = QWidget()
        root_widget.setLayout(root_layout)
        self.setCentralWidget(root_widget)

    def on_edit_done(self, new_df: pd.DataFrame = None, refresh_table: bool = True, refresh_tree: bool = True):
        pass

