import sys
import time

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QDataStream
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDialog, QPushButton, \
    QDialogButtonBox, QCheckBox, QMessageBox, QMenu, QAction

from defines import ANALYSIS_README, PRESET_TAG_PATH, ANALYSIS_SHOW_COLUMNS, GENERATE_DISPLAY_FIELD, \
    GENERATE_SHOW_COLUMNS
from df_utility import *
from TagManager import *
from app_utility import *
from ui_utility import CustomTableWidget, DraggableTree, DataFrameRowEditDialog


class GenerateWindow(QMainWindow):
    def __init__(self, tag_manager: TagManager):
        super().__init__()

        self.tag_manager = tag_manager
        self.display_tag = pd.DataFrame(columns=GENERATE_DISPLAY_FIELD)
        self.includes_sub_path = False

        # Create the root layout as a horizontal layout
        root_layout = QHBoxLayout()

        # Create the left group view named "Group" that wraps a DraggableTree
        group_view = QGroupBox("Group")
        group_view_layout = QVBoxLayout()

        self.tree = DraggableTree(self.tag_manager.get_database(), self.on_edit_done, parent=self)
        self.tree.setHeaderLabels(['Tag分类'])
        self.tree.setColumnCount(1)
        self.tree.itemClicked.connect(self.on_tree_click)

        group_view_layout.addWidget(self.tree)
        group_view.setLayout(group_view_layout)
        root_layout.addWidget(group_view, 20)

        # Create the center group view named "Tags" that wraps a CustomTableWidget
        tags_view = QGroupBox("Tags")
        tags_view_layout = QVBoxLayout()

        self.tag_table = CustomTableWidget()
        self.tag_table.setColumnCount(2)
        self.tag_table.setRowCount(0)
        self.tag_table.horizontalHeader().setSectionsClickable(True)
        self.tag_table.horizontalHeader().sectionClicked.connect(self.tag_table.sortByColumn)

        self.tag_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tag_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tag_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tag_table.setDragEnabled(True)
        self.tag_table.setDefaultDropAction(Qt.MoveAction)

        self.tag_table.cellDoubleClicked.connect(self.on_tag_table_double_click)
        self.tag_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tag_table.customContextMenuRequested.connect(self.on_tag_table_right_click)
        
        tags_view_layout.addWidget(self.tag_table)
        tags_view.setLayout(tags_view_layout)
        root_layout.addWidget(tags_view, 50)

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

    def on_widget_activated(self):
        self.refresh_ui()

    def on_edit_done(self, new_df: pd.DataFrame = None, refresh_table: bool = True, refresh_tree: bool = True):
        pass

    def on_tree_click(self, item: QTreeWidgetItem):
        df = self.tag_manager.get_database()
        full_path = self.tree.get_node_path(item)

        # If includes_sub_path is true, filter df by 'path' value starts with full_path
        # else filter df by 'path' value equals full_path
        if self.includes_sub_path:
            self.display_tag = df[df['path'].str.startswith(full_path)]
        else:
            self.display_tag = df[df['path'] == full_path]
        self.display_tag = self.display_tag.reset_index()

        self.refresh_table()

    def on_tag_table_right_click(self):
        pass

    def on_tag_table_double_click(self):
        pass

    def refresh_ui(self):
        self.refresh_tree()
        self.refresh_table()

    def refresh_tree(self):
        TagManager.update_tag_path_tree(self.tree, self.tag_manager.get_database(), PRESET_TAG_PATH)

    def refresh_table(self):
        TagManager.dataframe_to_table_widget(self.tag_table, self.display_tag, GENERATE_SHOW_COLUMNS, [])

