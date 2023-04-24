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


class AnalyserWindow(QWidget):
    def __init__(self, tag_manager: TagManager):
        super().__init__()

        self.tag_manager = tag_manager
        # self.tag_manager.register_database_observer(self)

        self.positive_tags = []
        self.negative_tags = []
        self.extra_data = ''
        self.positive_df = pd.DataFrame(columns=DATABASE_FIELDS)
        self.negative_df = pd.DataFrame(columns=DATABASE_FIELDS)

        self.row_color = QtGui.QColor(255, 255, 255)

        # Create the root layout
        root_layout = QVBoxLayout(self)
        # Create the top horizontal layout
        top_layout = QHBoxLayout()
        # Add the multiple text edit to the top layout
        self.text_edit = QPlainTextEdit()
        top_layout.addWidget(self.text_edit, 3)

        # Create the read-only multiple line text for the analysis readme
        text_comments = QPlainTextEdit()
        text_comments.setReadOnly(True)
        text_comments.setPlainText(ANALYSIS_README)
        top_layout.addWidget(text_comments, 7)

        # Set the space ratio to 55% and 45%
        top_layout.setStretch(0, 55)
        top_layout.setStretch(1, 45)
        # Add the top layout to the root layout
        root_layout.addLayout(top_layout)

        # Create the menu layout as a horizontal layout
        menu_layout = QHBoxLayout()
        # Add the '自动翻译' button to the menu layout and link it to the on_button_translate function
        auto_translate_button = QPushButton('自动翻译')
        auto_translate_button.clicked.connect(self.on_button_translate)
        menu_layout.addWidget(auto_translate_button)

        # self.group_check_button = QCheckBox('按组排列')
        # self.group_check_button.setChecked(True)
        # self.group_check_button.clicked.connect(self.on_check_group)
        # menu_layout.addWidget(self.group_check_button)

        # Add a stretch that weights max to the menu layout
        menu_layout.addStretch(1)
        # Add the menu layout to the root layout between the top and bottom layouts
        root_layout.addLayout(menu_layout)

        # Create the group widget for the positive table
        self.positive_group = QGroupBox("Positive", parent=self)
        # Create the multiple column table for the positive group
        self.positive_table = CustomTableWidget(parent=self)
        self.positive_table.setColumnCount(2)
        self.positive_table.setRowCount(0)
        positive_group_layout = QVBoxLayout()
        positive_group_layout.addWidget(self.positive_table)
        self.positive_group.setLayout(positive_group_layout)

        # Create the group widget for the negative table
        self.negative_group = QGroupBox("Negative", parent=self)
        # Create the multiple column table for the negative group
        self.negative_table = CustomTableWidget(parent=self)
        self.negative_table.setColumnCount(2)
        self.negative_table.setRowCount(5)
        negative_group_layout = QVBoxLayout()
        negative_group_layout.addWidget(self.negative_table)
        self.negative_group.setLayout(negative_group_layout)

        # Set the horizontal header of the positive and negative tables to be clickable for sorting
        self.positive_table.horizontalHeader().setSectionsClickable(True)
        self.negative_table.horizontalHeader().setSectionsClickable(True)

        # Connect the sort function to the header clicked signal of the positive and negative tables
        self.positive_table.horizontalHeader().sectionClicked.connect(self.positive_table.sortByColumn)
        self.negative_table.horizontalHeader().sectionClicked.connect(self.negative_table.sortByColumn)

        # Create the tree widget for the tree group
        self.tree_group = QGroupBox("Tree", parent=self)
        # Create the tree widget for the tree group
        self.tree = DraggableTree(self.tag_manager.get_database(), self.on_edit_done, parent=self)
        # Create the tree widget for the tree group with one column and the specified name
        self.tree.setHeaderLabels(['Tag分类'])
        self.tree.setColumnCount(1)
        tree_group_layout = QVBoxLayout()
        tree_group_layout.addWidget(self.tree)
        self.tree_group.setLayout(tree_group_layout)
        # Create the bottom horizontal layout
        bottom_layout = QHBoxLayout()
        # Add the positive group to the bottom layout
        bottom_layout.addWidget(self.positive_group)
        # Add the tree group to the bottom layout
        bottom_layout.addWidget(self.tree_group, 1)
        # Add the negative group to the bottom layout
        bottom_layout.addWidget(self.negative_group)
        # Set the space ratio to 1:1:1
        bottom_layout.setStretch(0, 45)
        bottom_layout.setStretch(1, 10)
        bottom_layout.setStretch(2, 45)
        # Add the bottom layout to the root layout
        root_layout.addLayout(bottom_layout)
        root_layout.setStretch(0, 2)
        root_layout.setStretch(1, 0)
        root_layout.setStretch(2, 8)

        # Connect the on_prompt_edit function to the textChanged signal of self.text_edit
        self.text_edit.textChanged.connect(self.on_prompt_edit)

        # Set both tables to be whole row selection, multiple selection, not editable, and draggable
        self.positive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.positive_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.positive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.positive_table.setDragEnabled(True)
        self.positive_table.setDefaultDropAction(Qt.MoveAction)

        self.negative_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.negative_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.negative_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.negative_table.setDragEnabled(True)
        self.negative_table.setDefaultDropAction(Qt.MoveAction)

        # Connect the on_positive_table_double_click function to the cellDoubleClicked signal of self.positive_table
        self.positive_table.cellDoubleClicked.connect(self.on_positive_table_double_click)

        # Connect the on_negative_table_double_click function to the cellDoubleClicked signal of self.negative_table
        self.negative_table.cellDoubleClicked.connect(self.on_negative_table_double_click)

        # Add right click handling to the positive table
        self.positive_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.positive_table.customContextMenuRequested.connect(self.on_positive_table_right_click)

        # Add right click handling to the negative table
        self.negative_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.negative_table.customContextMenuRequested.connect(self.on_negative_table_right_click)

        self.update_tag_path_tree()

    def on_widget_activated(self):
        pass

    # Define a function to be called when the text in self.text_edit changes
    def on_prompt_edit(self):
        # Call parse_prompts with the input of self.text_edit
        self.positive_tags, self.negative_tags, self.extra_data = \
            TagManager.parse_prompts(self.text_edit.toPlainText())
        self.rebuild_analysis_table(True, True, True)

    # Define a function to be called when a cell in the positive table is double clicked
    def on_positive_table_double_click(self, row, column):
        self.do_edit_item(self.positive_table, row, self.positive_df)

    # Define a function to be called when a cell in the negative table is double clicked
    def on_negative_table_double_click(self, row, column):
        self.do_edit_item(self.negative_table, row, self.negative_df)

    # Define a function to be called when the positive table is right clicked
    def on_positive_table_right_click(self, position):
        # Create a menu
        menu = QMenu()

        # Add actions to the menu
        copy_action = QAction('复制选中的正面tag', self)
        copy_action.triggered.connect(lambda: self.do_copy_tag(self.positive_table))
        menu.addAction(copy_action)

        # Add a menu item to the positive table menu
        save_translation_action = QAction('保存选中的翻译', self)
        save_translation_action.triggered.connect(
            lambda: self.do_save_selected_translation(self.positive_table, self.positive_df))
        menu.addAction(save_translation_action)

        # Show the menu at the position of the right click
        menu.exec_(self.positive_table.viewport().mapToGlobal(position))

    # Define a function to be called when the negative table is right clicked
    def on_negative_table_right_click(self, position):
        # Create a menu
        menu = QMenu()

        # Add actions to the menu
        copy_action = QAction('复制选中的反面tag', self)
        copy_action.triggered.connect(lambda: self.do_copy_tag(self.negative_table))
        menu.addAction(copy_action)

        # Add a menu item to the negative table menu
        save_translation_action = QAction('保存选中的翻译', self)
        save_translation_action.triggered.connect(
            lambda: self.do_save_selected_translation(self.negative_table, self.negative_df))
        menu.addAction(save_translation_action)

        # Show the menu at the position of the right click
        menu.exec_(self.negative_table.viewport().mapToGlobal(position))

    # Define a function to be called when the translate button is clicked
    def on_button_translate(self):
        # Pop up a message box with yes and no button
        reply = QMessageBox.question(self, 'Translation Confirmation',
                                     '将使用有道对未翻译的tag进行翻译，需要联网。机翻精度有限，仅供参考。\n'
                                     '由于采用同步的方式进行网络请求，在翻译过程中界面会无法操作，这是正常现象。\n'
                                     '翻译结果不会自动保存到数据库，需要通过编辑操作（双击编辑或拖动）来应用更改。\n\n'
                                     '是否继续？', QMessageBox.Yes | QMessageBox.No)
        # If the user clicks no, return
        if reply == QMessageBox.No:
            return

        self.translate_unknown_tags()

    def update_tag_path_tree(self):
        TagManager.update_tag_path_tree(self.tree, self.tag_manager.get_database(), PRESET_TAG_PATH)

    def get_selectd_tags(self, table: QTableWidget) -> [str]:
        selected_tags = [table.item(row.row(), 0).text() for row in table.selectionModel().selectedRows()]
        return selected_tags

    def do_edit_item(self, table: QTableWidget, row, df):
        item = table.item(row, 0)
        if item is not None:
            # Get the tag from the selected row
            tag = table.item(row, 0).text()
            selected_rows_df = df[df[PRIMARY_KEY] == tag]
            editor = DataFrameRowEditDialog(self.tag_manager.get_database(), DATABASE_SUPPORT_FIELD, selected_rows_df, PRIMARY_KEY)
            result = editor.exec_()

            if result == QDialog.Accepted:
                self.on_edit_done()

    def do_copy_tag(self, table: QTableWidget):
        # Get the selected row's first column values as a list
        selected_tags = self.get_selectd_tags(table)

        # Join the list by ','
        joined_string = ','.join(selected_tags)

        # Copy the joined string to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(joined_string)

    def do_save_selected_translation(self, table: QTableWidget, df: pd.DataFrame):
        # Get the selected tags
        selected_tags = self.get_selectd_tags(table)

        # Select the 'tag' and 'translate_cn' columns where 'tag' is in selected_tags
        selected_df = df.loc[df['tag'].isin(selected_tags), [PRIMARY_KEY, 'translate_cn']]

        if not selected_df.empty:
            new_df = upsert_df_from_right(self.tag_manager.get_database(), selected_df, PRIMARY_KEY)
            self.on_database_updated(new_df, False)

    def translate_unknown_tags(self):
        if translate_df(self.positive_df, PRIMARY_KEY, 'translate_cn', True) and \
                translate_df(self.negative_df, PRIMARY_KEY, 'translate_cn', True):
            TagManager.dataframe_to_table_widget(
                self.positive_table, self.positive_df, ANALYSIS_SHOW_COLUMNS, [], self.df_to_table_decorator)
            TagManager.dataframe_to_table_widget(
                self.negative_table, self.negative_df, ANALYSIS_SHOW_COLUMNS, [], self.df_to_table_decorator)
        else:
            QMessageBox.information(self, 'Translation Fail',
                                    '翻译失败，可能是网络问题。请确保你的网络可以访问有道翻译。',
                                    QMessageBox.Ok)

    # ---------------------------------------------------------------------------------------------

    def df_to_table_decorator(self, row, col, item):
        if col == 0:
            tag = item.text()
            if tag in self.tag_manager.get_database()[PRIMARY_KEY].values:
                self.row_color = QtGui.QColor(0xCC, 0xFF, 0x99)
            else:
                self.row_color = QtGui.QColor(255, 255, 255)
        item.setBackground(self.row_color)

    def on_edit_done(self, new_df: pd.DataFrame = None, refresh_table: bool = True, refresh_tree: bool = True):
        self.on_database_updated(new_df, refresh_tree)
        self.rebuild_analysis_table(True, True, refresh_table)

    def on_database_updated(self, new_df: pd.DataFrame = None, refresh_ui: bool = True):
        self.tag_manager.inform_database_modified(new_df, True)
        self.tree.database = self.tag_manager.get_database()
        if refresh_ui:
            self.update_tag_path_tree()

    def rebuild_analysis_table(self, positive: bool, negative: bool, refresh_ui: bool = True):
        # Based on positive_tags and negative_tags

        # Join positive_df with tag_database by PRIMARY_KEY row. Keep all tag_database columns.
        # If the tag not in tag_database, the columns are empty string. The same to negative_df.

        if positive:
            positive_tag_data_dict = TagManager.tags_list_to_tag_data(unique_list(self.positive_tags))
            if not self.tag_manager.get_database().empty:
                positive_translate_df = self.positive_df[[PRIMARY_KEY, 'translate_cn']].copy()
                self.positive_df = pd.DataFrame(positive_tag_data_dict)
                self.positive_df = merge_df_keeping_left_value(
                    self.positive_df, self.tag_manager.get_database(), PRIMARY_KEY)
                self.positive_df = update_df_from_right_value_if_empty(self.positive_df, positive_translate_df,
                                                                       PRIMARY_KEY)
            else:
                self.positive_df = pd.DataFrame(positive_tag_data_dict, columns=DATABASE_FIELDS).fillna('')
            if refresh_ui:
                TagManager.dataframe_to_table_widget(
                    self.positive_table, self.positive_df, ANALYSIS_SHOW_COLUMNS, [], self.df_to_table_decorator)

        if negative:
            negative_tag_data_dict = TagManager.tags_list_to_tag_data(unique_list(self.negative_tags))
            if not self.tag_manager.get_database().empty:
                negative_translate_df = self.negative_df[[PRIMARY_KEY, 'translate_cn']].copy()
                self.negative_df = pd.DataFrame(negative_tag_data_dict)
                self.negative_df = merge_df_keeping_left_value(
                    self.negative_df, self.tag_manager.get_database(), PRIMARY_KEY)
                self.negative_df = update_df_from_right_value_if_empty(self.negative_df, negative_translate_df,
                                                                       PRIMARY_KEY)
            else:
                self.negative_df = pd.DataFrame(negative_tag_data_dict, columns=DATABASE_FIELDS).fillna('')
            if refresh_ui:
                TagManager.dataframe_to_table_widget(
                    self.negative_table, self.negative_df, ANALYSIS_SHOW_COLUMNS, [], self.df_to_table_decorator)

    def on_database_changed(self):
        pass
