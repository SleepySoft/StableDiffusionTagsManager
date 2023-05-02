import sys
import time

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QDataStream
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDialog, QPushButton, \
    QDialogButtonBox, QCheckBox, QMessageBox, QMenu, QAction, QInputDialog

from defines import ANALYSIS_README, PRESET_TAG_PATH, ANALYSIS_SHOW_COLUMNS, GENERATE_DISPLAY_FIELD, \
    GENERATE_SHOW_COLUMNS, GENERATE_EDIT_FIELDS, GENERATE_EDIT_COLUMNS
from df_utility import *
from TagManager import *
from app_utility import *
from ui_components import TagViewTableWidget, DraggableTree, DataFrameRowEditDialog, CustomPlainTextEdit, \
    TagEditTableWidget


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

        self.tag_table = TagViewTableWidget()
        self.tag_table.setColumnCount(2)
        self.tag_table.setRowCount(0)
        self.tag_table.horizontalHeader().setSectionsClickable(True)
        self.tag_table.horizontalHeader().sectionClicked.connect(self.tag_table.sortByColumn)

        self.tag_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tag_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tag_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # self.tag_table.setDragEnabled(True)
        # self.tag_table.setDefaultDropAction(Qt.MoveAction)

        self.tag_table.cellDoubleClicked.connect(self.on_tag_table_double_click)
        self.tag_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tag_table.customContextMenuRequested.connect(self.on_tag_table_right_click)
        
        tags_view_layout.addWidget(self.tag_table)
        tags_view.setLayout(tags_view_layout)
        root_layout.addWidget(tags_view, 50)

        # Create the right vertical layout
        right_layout = QVBoxLayout()

        # Create the top group view named "Action"
        action_view = QGroupBox("Action")
        action_view_layout = QVBoxLayout()

        # Create a button named "生成"
        generate_button = QPushButton("生成", self)
        # Connect the button to the on_generate function
        generate_button.clicked.connect(self.do_generate)
        # Add the button to the action_view_layout
        action_view_layout.addWidget(generate_button)


        action_view.setLayout(action_view_layout)
        right_layout.addWidget(action_view, 20)

        # Create the group view named "Positive" that wraps a multiple line text editor
        positive_view = QGroupBox("正向Tag")
        positive_view_layout = QVBoxLayout()

        self.positive_table = TagEditTableWidget(self.tag_manager, GENERATE_EDIT_COLUMNS)

        self.positive_table.horizontalHeader().setSectionsClickable(True)
        self.positive_table.horizontalHeader().sectionClicked.connect(self.positive_table.sortByColumn)

        self.positive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.positive_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.positive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.positive_table.cellDoubleClicked.connect(self.on_tag_table_double_click)
        self.positive_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.positive_table.customContextMenuRequested.connect(self.on_positive_table_right_click)

        positive_view_layout.addWidget(self.positive_table)
        positive_view.setLayout(positive_view_layout)
        right_layout.addWidget(positive_view, 50)

        # Create the group view named "Negative" that wraps a multiple line text editor
        negative_view = QGroupBox("反向Tag")
        negative_view_layout = QVBoxLayout()

        self.negative_table = TagEditTableWidget(self.tag_manager, GENERATE_EDIT_COLUMNS)

        self.negative_table.horizontalHeader().setSectionsClickable(True)
        self.negative_table.horizontalHeader().sectionClicked.connect(self.negative_table.sortByColumn)

        self.negative_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.negative_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.negative_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.negative_table.cellDoubleClicked.connect(self.on_tag_table_double_click)
        self.negative_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.negative_table.customContextMenuRequested.connect(self.on_negative_table_right_click)

        negative_view_layout.addWidget(self.negative_table)
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

    def on_edit_done(self, refresh_tree: bool = False):
        self.tag_manager.inform_database_modified(None, True)
        translated_df = self.display_tag[[PRIMARY_KEY, 'translate_cn']].copy()
        self.display_tag = update_df_from_right_value(
            self.display_tag, self.tag_manager.get_database(), PRIMARY_KEY)
        self.display_tag = update_df_from_right_value_if_empty(self.display_tag, translated_df, PRIMARY_KEY)

        if refresh_tree:
            self.refresh_tree()
        self.refresh_table()

    def on_tree_click(self, item: QTreeWidgetItem):
        df = self.tag_manager.get_database()
        full_path = self.tree.get_node_path(item)

        # If includes_sub_path is true, filter df by 'path' value starts with full_path
        # else filter df by 'path' value equals full_path
        if self.includes_sub_path:
            self.display_tag = df[df['path'].str.startswith(full_path)]
        else:
            self.display_tag = df[df['path'] == full_path]
        self.display_tag = self.display_tag.reset_index(drop=True)

        self.refresh_table()

    def on_tag_table_double_click(self, row, column):
        item = self.tag_table.item(row, 0)
        if item is not None:
            # Get the tag from the selected row
            tag = self.tag_table.item(row, 0).text()
            selected_rows_df = self.display_tag[self.display_tag[PRIMARY_KEY] == tag]
            editor = DataFrameRowEditDialog(
                self.tag_manager.get_database(), DATABASE_SUPPORT_FIELD, selected_rows_df, PRIMARY_KEY)
            result = editor.exec_()

            if result == QDialog.Accepted:
                self.on_edit_done()

    def on_tag_table_right_click(self, position):
        # Create a menu
        menu = QMenu()

        # Add a menu item to the positive table menu
        translation_action = QAction('翻译选中的Tag（如果当前没翻译）', self)
        translation_action.triggered.connect(
            lambda: self.do_translation_action())
        menu.addAction(translation_action)

        save_translation_action = QAction('保存选中Tag的翻译（如果有）', self)
        save_translation_action.triggered.connect(
            lambda: self.save_translation_action())
        menu.addAction(save_translation_action)

        # Show the menu at the position of the right click
        menu.exec_(self.tag_table.viewport().mapToGlobal(position))

    def on_positive_table_right_click(self, position):
        self.on_table_right_click(self.positive_table, position)

    def on_negative_table_right_click(self, position):
        self.on_table_right_click(self.negative_table, position)

    def on_table_right_click(self, table: TagViewTableWidget, position):
        # Create a menu
        menu = QMenu()

        # Add a menu item to the positive table menu
        set_shuffle_action = QAction('设置抽签分组', self)
        set_shuffle_action.triggered.connect(
            lambda: self.do_set_shuffle(table))
        menu.addAction(set_shuffle_action)

        remove_shuffle_action = QAction('删除抽签分组', self)
        remove_shuffle_action.triggered.connect(
            lambda: self.do_remove_shuffle(table))
        menu.addAction(remove_shuffle_action)

        # Show the menu at the position of the right click
        menu.exec_(table.viewport().mapToGlobal(position))

    def refresh_ui(self):
        self.refresh_tree()
        self.refresh_table()

    def refresh_tree(self):
        TagManager.update_tag_path_tree(self.tree, self.tag_manager.get_database(), PRESET_TAG_PATH)

    def refresh_table(self):
        TagManager.dataframe_to_table_widget(self.tag_table, self.display_tag, GENERATE_SHOW_COLUMNS, [])

    def do_translation_action(self):
        # Get the selected tags
        selected_tags = self.tag_table.get_selected_row_field_value(0)

        selected_df = self.display_tag.loc[self.display_tag['tag'].isin(selected_tags)]
        if translate_df(selected_df, PRIMARY_KEY, 'translate_cn', True):
            self.display_tag = update_df_from_right_value_if_empty(
                self.display_tag, selected_df, PRIMARY_KEY, ['translate_cn'])
            self.refresh_table()

    def save_translation_action(self):
        tag_database = self.tag_manager.get_database()

        # Get the selected tags
        selected_tags = self.tag_table.get_selected_row_field_value(0)

        # Filter the display_tag dataframe to only include rows where the tag is in the selected_tags list
        selected_df = self.display_tag.loc[self.display_tag[PRIMARY_KEY].isin(selected_tags)]

        if not selected_df.empty:
            new_df = update_df_from_right_value(tag_database, selected_df, PRIMARY_KEY, ['translate_cn'])
            new_df = new_df.reset_index(drop=True)

            self.tag_manager.inform_database_modified(new_df, True)

            # Refresh the table to display the updated data
            self.refresh_table()

    def do_set_shuffle(self, table: TagEditTableWidget):
        text, ok = QInputDialog.getText(self, '抽签分组', '请输入抽签分组名')
        if ok and text and text.strip():
            table.set_data_by_selected_row(3, text.strip())

    def do_remove_shuffle(self, table: TagEditTableWidget):
        table.set_data_by_selected_row(3, '')

    def do_generate(self):
        if not os.path.exists('wildcards'):
            os.mkdir('wildcards')
        self.positive_table.generate('positive.txt', 'wildcards')
        self.negative_table.generate('negative.txt', 'wildcards')

        # Open positive.txt file
        os.startfile('positive.txt')
        
        # Open negative.txt file
        os.startfile('negative.txt')

        




