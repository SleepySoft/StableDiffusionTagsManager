import sys
import time

import pandas as pd
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import Qt, QDataStream
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDialog, QPushButton, \
    QDialogButtonBox, QCheckBox, QMessageBox, QMenu, QAction, QInputDialog

from Prompts import Prompts
from SaveTagsWindow import SavePromptsDialog
from defines import ANALYSIS_README, PRESET_TAG_PATH, ANALYSIS_SHOW_COLUMNS, GENERATE_DISPLAY_FIELD, \
    GENERATE_SHOW_COLUMNS, GENERATE_EDIT_FIELDS, GENERATE_EDIT_COLUMNS
from df_utility import *
from TagManager import *
from app_utility import *
from ui_components import TagViewTableWidget, DraggableTree, DataFrameRowEditDialog, PromptPlainTextEdit, \
    TagEditTableWidget


class GenerateWindow(QMainWindow):
    def __init__(self, tag_manager: TagManager):
        super().__init__()

        self.tag_manager = tag_manager
        self.display_tag = pd.DataFrame(columns=GENERATE_DISPLAY_FIELD)
        self.includes_sub_path = False

        # Create the root layout as a horizontal layout
        root_layout = QHBoxLayout()

        # ----------------- Left part - group group box -----------------

        # Create the left group view named "Group" that wraps a DraggableTree
        group_view = QGroupBox("Group")
        group_view_layout = QVBoxLayout()
        group_view.setLayout(group_view_layout)

        # ------------------------- Database Tree -------------------------

        self.tree_db = DraggableTree(self.tag_manager.get_database(), self.on_edit_done, parent=self)
        self.tree_db.setHeaderLabels(['Tag分类'])
        self.tree_db.setColumnCount(1)
        self.tree_db.itemClicked.connect(self.on_tree_click)

        # --------------------------- Depot Tree ---------------------------

        self.tree_depot_browse = DraggableTree(self.tag_manager.get_database(), self.on_edit_done, parent=self)
        self.tree_depot_browse.setHeaderLabels(['Tag分类'])
        self.tree_depot_browse.setColumnCount(1)

        self.tree_depot_browse.itemClicked.connect(self.on_tree_depot_browse_item_clicked)
        # self.tree_depot_browse.itemDragged.connect(self.on_tree_depot_browse_item_dragged)

        # Create the first tab named 'Tag数据库'
        tag_database_tab = QWidget()
        tag_database_tab_layout = QHBoxLayout()
        tag_database_tab_layout.addWidget(self.tree_db)
        tag_database_tab.setLayout(tag_database_tab_layout)

        # Create the second tab named 'Tag收藏' with vertical layout.
        tag_collection_tab = QWidget()
        tag_collection_tab_layout = QVBoxLayout()
        tag_collection_tab_layout.addWidget(self.tree_depot_browse)
        tag_collection_tab.setLayout(tag_collection_tab_layout)

        # tag_free_input_tab = QWidget()
        # tag_free_input_tab_layout = QVBoxLayout()
        # tag_free_input_tab_layout.addWidget(self.tree_depot_browse)
        # tag_free_input_tab.setLayout(tag_free_input_tab_layout)

        # Create the tab widget and add the two tabs
        tab_widget = QTabWidget()
        tab_widget.addTab(tag_database_tab, "Tag数据库")
        tab_widget.addTab(tag_collection_tab, "Tag收藏")
        # tab_widget.addTab(tag_free_input_tab, "自由输入")
        tab_widget.currentChanged.connect(self.on_tab_changed)

        group_view_layout.addWidget(tab_widget)

        root_layout.addWidget(group_view, 20)

        # ---------------------------------------------------------------------------

        structured_data_tab = QWidget()
        structured_data_tab_layout = QVBoxLayout()
        structured_data_tab.setLayout(structured_data_tab_layout)

        raw_data_tab = QWidget()
        raw_data_tab_layout = QHBoxLayout()
        raw_data_tab.setLayout(raw_data_tab_layout)

        self.tab_structured_raw_widget = QTabWidget()
        self.tab_structured_raw_widget.addTab(structured_data_tab, "结构化数据")
        self.tab_structured_raw_widget.addTab(raw_data_tab, "原始数据")
        self.tab_structured_raw_widget.setTabVisible(1, False)

        # ---------------------- The tag group ----------------------

        # Create the center group view named "Tags" that wraps a CustomTableWidget
        group_tags_view = QGroupBox("Tags")
        group_tags_view_layout = QVBoxLayout()
        group_tags_view.setLayout(group_tags_view_layout)

        self.tag_table = TagViewTableWidget(list(GENERATE_SHOW_COLUMNS.keys()))
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

        group_tags_view_layout.addWidget(self.tag_table)

        # ------------------ The information group ------------------

        # the bottom is a groupbox named '信息' which includes a read only multiple line text named text_information
        self.group_information = QGroupBox("信息")
        group_information_layout = QVBoxLayout()
        self.group_information.setVisible(False)
        self.group_information.setLayout(group_information_layout)

        self.text_information = QPlainTextEdit()
        self.text_information.setReadOnly(True)

        group_information_layout.addWidget(self.text_information)

        # -----------------------------------------------------------

        structured_data_tab_layout.addWidget(group_tags_view, 55)
        structured_data_tab_layout.addWidget(self.group_information, 45)

        # -------------------- The raw data group --------------------

        self.text_raw_sdtags = QPlainTextEdit()
        raw_data_tab_layout.addWidget(self.text_raw_sdtags)

        # -----------------------------------------------------------

        # self.text_free = QPlainTextEdit()
        # tag_free_input_tab_layout.addWidget(self.text_free)

        root_layout.addWidget(self.tab_structured_raw_widget, 35)

        # ---------------------------------------------------------------------------

        # Create the right vertical layout
        right_layout = QVBoxLayout()

        # Create the top group view named "Action"
        action_view = QGroupBox("Action")
        action_view_layout = QHBoxLayout()

        line = QVBoxLayout()
        # # Create a button named "生成"
        # generate_button = QPushButton("生成", self)
        # # Connect the button to the on_generate function
        # generate_button.clicked.connect(self.do_generate)
        # # Add the button to the action_view_layout
        # line.addWidget(generate_button)

        generate_button = QPushButton("保存为", self)
        generate_button.clicked.connect(self.do_save)
        line.addWidget(generate_button)

        action_view_layout.addLayout(line)

        action_view.setLayout(action_view_layout)
        right_layout.addWidget(action_view, 20)

        # Create the group view named "Positive" that wraps a multiple line text editor
        positive_view = QGroupBox("正向Tag")
        positive_view_layout = QVBoxLayout()

        # self.positive_table = TagEditTableWidget(self.tag_manager, GENERATE_EDIT_COLUMNS)
        #
        # self.positive_table.horizontalHeader().setSectionsClickable(True)
        # self.positive_table.horizontalHeader().sectionClicked.connect(self.positive_table.sortByColumn)
        #
        # self.positive_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.positive_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # self.positive_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        #
        # self.positive_table.cellDoubleClicked.connect(self.on_tag_table_double_click)
        # self.positive_table.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.positive_table.customContextMenuRequested.connect(self.on_positive_table_right_click)
        #
        # positive_view_layout.addWidget(self.positive_table)

        self.text_positive_prompts = PromptPlainTextEdit(True)
        positive_view_layout.addWidget(self.text_positive_prompts)

        positive_view.setLayout(positive_view_layout)
        right_layout.addWidget(positive_view, 50)

        # Create the group view named "Negative" that wraps a multiple line text editor
        negative_view = QGroupBox("反向Tag")
        negative_view_layout = QVBoxLayout()

        # self.negative_table = TagEditTableWidget(self.tag_manager, GENERATE_EDIT_COLUMNS)
        #
        # self.negative_table.horizontalHeader().setSectionsClickable(True)
        # self.negative_table.horizontalHeader().sectionClicked.connect(self.negative_table.sortByColumn)
        #
        # self.negative_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.negative_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # self.negative_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        #
        # self.negative_table.cellDoubleClicked.connect(self.on_tag_table_double_click)
        # self.negative_table.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.negative_table.customContextMenuRequested.connect(self.on_negative_table_right_click)
        #
        # negative_view_layout.addWidget(self.negative_table)

        self.text_negative_prompts = PromptPlainTextEdit(False)
        negative_view_layout.addWidget(self.text_negative_prompts)

        negative_view.setLayout(negative_view_layout)
        right_layout.addWidget(negative_view, 30)

        # Set the weight of the right layout to 40%
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        # Set the root layout
        root_widget = QWidget()
        root_widget.setLayout(root_layout)
        self.setCentralWidget(root_widget)

        root_layout.addWidget(right_widget, 45)

    def on_widget_activated(self):
        self.refresh_depot_tree()
        self.refresh_ui()

    # Callback Companionable.
    def on_edit_done(self, _: pd.DataFrame = None, refresh_tree: bool = False):
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
        full_path = self.tree_db.get_node_path(item)

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

    # def on_positive_table_right_click(self, position):
    #     self.on_table_right_click(self.positive_table, position)
    #
    # def on_negative_table_right_click(self, position):
    #     self.on_table_right_click(self.negative_table, position)

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

    def on_tab_changed(self, index):
        if index == 1:
            self.refresh_tree()
            self.group_information.setVisible(True)
            self.tab_structured_raw_widget.setTabVisible(1, True)
        else:
            self.group_information.setVisible(False)
            self.tab_structured_raw_widget.setTabVisible(1, False)

    def refresh_ui(self):
        self.refresh_tree()
        self.refresh_table()

    def refresh_tree(self):
        TagManager.update_tag_path_tree(self.tree_db, self.tag_manager.get_database(), PRESET_TAG_PATH)

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

            QMessageBox.information(self, '保存结果', '保存完成。')

            # Refresh the table to display the updated data
            self.refresh_table()
        else:
            QMessageBox.information(self, '提示', '没有选择任何项目。')

    def do_set_shuffle(self, table: TagEditTableWidget):
        text, ok = QInputDialog.getText(self, '抽签分组', '请输入抽签分组名')
        if ok and text and text.strip():
            table.set_data_by_selected_row(3, text.strip())

    def do_remove_shuffle(self, table: TagEditTableWidget):
        table.set_data_by_selected_row(3, '')

    # def do_generate(self):
    #     if not os.path.exists('wildcards'):
    #         os.mkdir('wildcards')
    #     self.positive_table.generate_files('positive.txt', 'wildcards')
    #     self.negative_table.generate_files('negative.txt', 'wildcards')
    #
    #     # Open positive.txt file
    #     os.startfile('positive.txt')
    #
    #     # Open negative.txt file
    #     os.startfile('negative.txt')

    def do_save(self):
        prompt = Prompts()
        prompt.from_text(self.text_positive_prompts.toPlainText() + '\n\n' + self.text_negative_prompts.toPlainText())
        # prompt.positive_tag_data_dict = self.positive_table.table_editing_data[[PRIMARY_KEY, 'weight']].to_dict('records')
        # prompt.positive_tag_data_dict = self.negative_table.table_editing_data[[PRIMARY_KEY, 'weight']].to_dict('records')
        dlg = SavePromptsDialog(prompt)
        dlg.exec_()

    # def refresh_depot_tree(self):
    #     self.tree_depot_browse.clear()
    #     depot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'depot')
    #     for root, dirs, files in os.walk(depot_path):
    #         for file in files:
    #             if file.endswith('.sdtags'):
    #                 file_path = os.path.join(root, file)
    #                 item = QTreeWidgetItem(self.tree_depot_browse)
    #                 item.setText(0, os.path.relpath(file_path, depot_path))
    #                 item.setData(0, Qt.UserRole, file_path)
    
    def add_items(self, parent, path):
        for name in os.listdir(path):
            file_path = os.path.join(path, name)
            if os.path.isdir(file_path):
                item = QTreeWidgetItem(parent)
                item.setText(0, name)
                self.add_items(item, file_path)
            elif name.endswith('.sdtags'):
                item = QTreeWidgetItem(parent)
                item.setText(0, name)
                item.setData(0, Qt.UserRole, file_path)

    def refresh_depot_tree(self):
        self.tree_depot_browse.clear()
        depot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'depot')
        self.add_items(self.tree_depot_browse, depot_path)

    def on_tree_depot_browse_item_clicked(self, item, column):
        file_path = item.data(0, Qt.UserRole)
        if file_path is not None:
            self.on_depot_file_selected(file_path)

    def on_tree_depot_browse_item_dragged(self, item, column):
        if item.childCount() == 0:
            file_path = item.data(0, Qt.UserRole)
            if file_path is not None:
                print('TODO: Dragged file:', file_path)

    def on_depot_file_selected(self, file_path):
        try:
            with open(file_path, 'rt') as f:
                file_data = f.read()
                self.text_raw_sdtags.setPlainText(file_data)

                prompt = Prompts()
                if prompt.from_text(file_data):
                    df = self.tag_manager.get_database()
                    self.display_tag = pd.DataFrame(prompt.positive_tag_data_dict)
                    self.display_tag = merge_df_keeping_left_value(self.display_tag, df, PRIMARY_KEY)
                    translate_df(self.display_tag, PRIMARY_KEY, 'translate_cn', True, True)
                    self.refresh_table()
                    self.text_information.setPlainText(prompt.extra_data_string)
        except Exception as e:
            print(e)
            return False
        finally:
            pass

    # def read_file_content(self, file_path):
    #     if os.path.isfile(file_path):
    #         with open(file_path, 'r', encoding='utf-8') as f:
    #             content = f.readlines()
    #             tags = content[0].strip().split(',')
    #             extra = '\n'.join(l.strip() for l in content[1:] if l.strip() != '') if len(content) > 1 else None
    #             return tags, extra
    #     return None, None


        




