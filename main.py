import re
import os
import sys
import time
import shutil
import glob
import datetime
import pandas as pd
from collections import OrderedDict

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QDataStream
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDialog, QPushButton, \
    QDialogButtonBox

PUBLIC_DATABASE = 'public.csv'
PRIVATE_DATABASE = 'private.csv'
BACKUP_LIMIT = 20

DATABASE_SUPPORT_FIELD = OrderedDict([
    ('tag', '标签'),
    ('path', '功能分组'),
    ('value', '标签价值'),
    ('translate_cn', '翻译'),
    ('comments', '备注'),
    ('weight', '默认权重'),
    ('label', '收藏夹'),
    ('private', '私有（Y/N）'),
    ('statistics', '统计')
])

DATABASE_FIELDS = list(DATABASE_SUPPORT_FIELD.keys())

ANALYSIS_DISPLAY_FIELD = ['tag', 'weight', 'path', 'value', 'translate_cn', 'comments']

ANALYSIS_SHOW_COLUMNS = OrderedDict()
for f in ANALYSIS_DISPLAY_FIELD:
    ANALYSIS_SHOW_COLUMNS[f] = DATABASE_SUPPORT_FIELD[f]
ANALYSIS_SHOW_COLUMNS['weight'] = '权重'

PRESET_TAG_PATH = ['正向效果', '反向效果', '中立效果',
                   '场景/室外', '场景/室内', '场景/幻境',
                   '角色/女性', '角色/男性', '角色/福瑞',
                   '脸部/头发', '脸部/眼睛', '脸部/嘴巴', '脸部/表情',
                   '衣服', '动作', '视角', '绘画风格', '18x']

ANALYSIS_README = """使用说明：
1. 将tags粘贴到左边的输入框中。第一行为正面tag，第二行为负面tag，忽略空行以及三行之后的附加数据。可以直接粘贴从C站上复制下来的图片参数。
2. 下方左侧列表显示正面tag分析结果，右侧列表显示负面tag分析结果。如果数据库中有对应tag的数据，则展示更多信息，否则除权重外显示空白。
   注：仅能分析基本的tag权重，对于特殊tag格式（过渡，LoRA）的分析并不完善。
3. 下方中间的树形控件显示预置及数据库中已存在的tag分组，将两侧的tag（可以多选）拖到分组结点上可以将tag快速分组并加入数据库。
4. 双击tag列表可以编辑该tag的详细信息，点击确定后该tag信息会更新到数据库。
   注：如果不对新tag进行3或4的操作，则这个tag不会放入数据库。建议只把有用的tag加入数据库。你也可以通过excel修改数据库的csv文件。
"""


# Do not use set to keep list order
def unique_list(lst: list or tuple) -> list:
    result = []
    [result.append(item) for item in lst if item not in result]
    return result


def format_float(value):
    try:
        value = float(value)
        return f"{value:.2f}"
    except ValueError:
        return str(value)


def backup_file(file_name: str, backup_limit: int):
    # Get the path of the file
    file_path = os.path.abspath(file_name)

    # Get the directory of the file
    file_dir = os.path.dirname(file_path)

    # Create the backup directory if it does not exist
    backup_dir = os.path.join(file_dir, 'backup')
    os.makedirs(backup_dir, exist_ok=True)

    # Get the timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S_%f')[:-3]

    # Get the file extension
    file_ext = os.path.splitext(file_name)[1]

    # Create the backup file name
    backup_file_name = os.path.basename(file_name)
    if file_ext:
        backup_file_name = backup_file_name.replace(file_ext, f'_{timestamp}{file_ext}')
    else:
        backup_file_name = f'{backup_file_name}_{timestamp}'

    # Copy the file to the backup directory
    backup_file_path = os.path.join(backup_dir, backup_file_name)
    shutil.copy2(file_path, backup_file_path)

    # Get the number of backup files
    if file_ext:
        backup_files = glob.glob(
            os.path.join(backup_dir, f'{os.path.basename(file_name).replace(file_ext, "")}_*{file_ext}'))
    else:
        backup_files = glob.glob(os.path.join(backup_dir, f'{os.path.basename(file_name)}_*'))
    num_backup_files = len(backup_files)

    # If the number of backup files is greater than the backup limit, delete the oldest file
    if num_backup_files > backup_limit:
        oldest_file = min(backup_files, key=os.path.getctime)
        os.remove(oldest_file)


def backup_file_safe(file_name: str, backup_limit: int) -> bool:
    try:
        backup_file(file_name, backup_limit)
        return True
    except Exception as e:
        print('Back file error.')
        print(e)
        return False
    finally:
        pass


def merge_df_keeping_left_value(left: pd.DataFrame, right: pd.DataFrame, on: str):
    df = left.merge(right, on=on, how='left', suffixes=('', '_y'))
    df = df.drop([col for col in df.columns if col.endswith('_y')], axis=1)
    df = df.fillna('')
    return df


def load_tag_data():
    # Load public.csv to df_public if it exists
    try:
        df_public = pd.read_csv(PUBLIC_DATABASE)
    except FileNotFoundError:
        df_public = pd.DataFrame(columns=['tag'])

    # Load private.csv to df_private if it exists
    try:
        df_private = pd.read_csv(PRIVATE_DATABASE)
    except FileNotFoundError:
        df_private = pd.DataFrame(columns=['tag'])

    # Join df_public and df_private by field "tag" to create df_tags
    df_tags = pd.concat([df_public, df_private])

    # Check if any of the required fields are missing in df_tags
    if not set(DATABASE_FIELDS).issubset(df_tags.columns):
        # Add the missing fields to df_tags
        df_tags = df_tags.reindex(columns=DATABASE_FIELDS)

    # Replace NaN or null values with empty strings
    df_tags = df_tags.fillna('')
    df_tags = df_tags.reindex()

    # Return the resulting DataFrame
    return df_tags


def save_tag_data(df: pd.DataFrame):
    # Split the dataframe into two based on the value of the 'private' field
    df_private = df[df['private'] == 'Y']
    df_public = df[df['private'] != 'Y']

    # Save the private and public dataframes to separate CSV files
    df_private.to_csv('private.csv', index=False, encoding='utf-8')
    df_public.to_csv('public.csv', index=False, encoding='utf-8')


def parse_prompts(prompt_text: str):
    # Split the prompt_text by '\n' and strip each line, remove empty lines
    lines = [line.strip() for line in prompt_text.split('\n') if line.strip()]

    def trim_colon(text: str) -> str:
        i1 = text.find(',')
        i2 = text.find(':')
        if 0 <= i2 < i1:
            text = text[text.index(':') + 1:]
        return text

    # Split line 0 by ',' and strip each sub string. line 0 is positive_tags, line 1 is negative_tags.
    positive_tags = [tag.strip() for tag in trim_colon(lines[0]).split(',')] if len(lines) > 0 else []
    negative_tags = [tag.strip() for tag in trim_colon(lines[1]).split(',')] if len(lines) > 1 else []

    # Join the rest lines by '\n' as extra_data. If no more lines extra_data should be empty string.
    extra_data = '\n'.join(lines[2:]) if len(lines) > 2 else ''

    # Return positive_tags, negative_tags, extra_data
    return positive_tags, negative_tags, extra_data


def analysis_tag(tag: str):
    # Check if the tag contains ":"
    if ":" in tag:
        # Remove the "()" surrounding the ":" if they exist
        tag = tag.strip("()")
        # Split the tag by ":" and check if the second part is a number
        parts = tag.split(":")
        try:
            # If the second part is a number, set the raw_tag and tag_weight accordingly
            raw_tag = parts[0]
            tag_weight = float(parts[1])
        except Exception:
            # If the second part is not a number, set the raw_tag to the entire tag and tag_weight to 1
            raw_tag = tag
            tag_weight = 1.0
        finally:
            pass
    # Check if the tag contains "|"
    elif "|" in tag:
        # If the tag contains "|", set the raw_tag to the entire tag and tag_weight to 1
        raw_tag = tag
        tag_weight = 1.0
    else:
        # If the tag does not contain ":" or "|", set the raw_tag to the content after removing all brackets
        raw_tag = re.sub(r'[\(\)\[\]]', '', tag)
        # Initialize the tag_weight to 1.0
        tag_weight = 1.0
        # Multiply the tag_weight by 1.1 for each layer of "()" surrounding the tag
        for i in range(tag.count("(")):
            tag_weight *= 1.1
        # Multiply the tag_weight by 0.9 for each layer of "[]" surrounding the tag
        for i in range(tag.count("[")):
            tag_weight *= 0.9
    # Return the raw_tag and tag_weight as a tuple
    return raw_tag.strip(), tag_weight


def tags_list_to_tag_data(tags: [str]) -> dict:
    data_tag = []
    data_weight = []
    for tag in tags:
        raw_tag, tag_weight = analysis_tag(tag)
        if len(raw_tag) == 0:
            continue
        # Process the duplicate case
        if raw_tag not in data_tag:
            data_tag.append(raw_tag)
            data_weight.append(format_float(tag_weight))
        else:
            index = data_tag.index(raw_tag)
            data_weight[index] = format_float(float(data_weight[index]) * float(tag_weight))
    return {
        'tag': data_tag,
        'weight': data_weight
    }


def dataframe_to_table_widget(
        table_widget: QTableWidget, dataframe: pd.DataFrame,
        field_mapping: OrderedDict, extra_headers: [str]):
    # Clear the table
    table_widget.clear()
    table_widget.setRowCount(0)

    # Set the column count for the table
    table_widget.setColumnCount(len(field_mapping) + len(extra_headers))

    # Set the horizontal header labels for the table
    header_labels = [field.capitalize() for field in field_mapping.values()] + extra_headers
    table_widget.setHorizontalHeaderLabels(header_labels)

    # Set the row count for the table
    table_widget.setRowCount(len(dataframe))

    # Fill the table with data from the dataframe
    for row in range(len(dataframe)):
        for col, field in enumerate(field_mapping.keys()):
            item = QTableWidgetItem(str(dataframe.loc[row, field]))
            table_widget.setItem(row, col, item)


class DataFrameRowEditDialog(QDialog):
    def __init__(self, df: pd.DataFrame, field_name_mapping: dict, unique_field: str, unique_field_value: any):
        super().__init__()

        self.database = df
        self.unique_field = unique_field
        self.unique_field_value = unique_field_value

        # Filter the dataframe by the unique field name and value
        filtered_df = df[df[unique_field] == unique_field_value]

        # If the filtered dataframe is empty, create a new row with the unique field value and empty fields
        if len(filtered_df) == 0:
            # Create a new dataframe with the same columns as df
            new_df = pd.DataFrame(columns=df.columns)
            # Add a new row with the unique field value and empty fields
            new_row = {}
            for col in new_df.columns:
                if col != unique_field:
                    new_row[col] = ''
            new_row[unique_field] = unique_field_value
            new_df = new_df.append(new_row, ignore_index=True)
            filtered_df = new_df

        # Get the first row of the filtered dataframe
        row = filtered_df.iloc[0]

        # Create the editable table widget
        self.table_widget = QTableWidget(len(row), 2, parent=self)

        # Set the horizontal header labels for the table
        header_labels = ['Field', 'Value']
        self.table_widget.setHorizontalHeaderLabels(header_labels)

        # Fill the table with data from the row
        for row_idx, (field, value) in enumerate(row.items()):
            if field in field_name_mapping.keys():
                display_name = field_name_mapping[field]
            else:
                display_name = field
            item = QTableWidgetItem(display_name)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setData(QtCore.Qt.UserRole, field)
            self.table_widget.setItem(row_idx, 0, item)

            item = QTableWidgetItem(str(value))
            if field == unique_field:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.table_widget.setItem(row_idx, 1, item)

        # Create the OK and Cancel buttons
        ok_button = QPushButton('OK', parent=self)
        cancel_button = QPushButton('Cancel', parent=self)

        # Create the button box and add the buttons
        button_box = QDialogButtonBox(Qt.Horizontal, parent=self)
        button_box.addButton(ok_button, QDialogButtonBox.AcceptRole)
        button_box.addButton(cancel_button, QDialogButtonBox.RejectRole)

        # Create the main layout and add the table widget and button box
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.table_widget)
        main_layout.addWidget(button_box)

        # Set the dialog size
        self.resize(400, 600)
        # Set the title of the dialog to 'Editor'
        self.setWindowTitle('Editor')
        # Set the dialog to be resizable
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

        # Connect the OK and Cancel buttons to their respective slots
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def accept(self):
        # Get the data from the table
        data = {}
        df = self.database
        for row_idx in range(self.table_widget.rowCount()):
            field_item = self.table_widget.item(row_idx, 0)
            value_item = self.table_widget.item(row_idx, 1)
            field_name = field_item.data(QtCore.Qt.UserRole)
            if field_item and value_item:
                data[field_name] = value_item.text().strip()

        index = df.index[df[self.unique_field] == self.unique_field_value].tolist()
        if not index:
            index = len(df)
        else:
            index = index[0]
        df.loc[index] = data

        # Call the base accept method to close the dialog
        super().accept()


class DraggableTree(QTreeWidget):
    def __init__(self, database: pd.DataFrame, on_edit_done, parent=None):
        super().__init__(parent)
        self.database = database
        self.on_operation_done = on_edit_done
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def dragEnterEvent(self, event):
        # Get the mime data from the event
        mime_data = event.mimeData()
        # If the mime data contains text/plain data
        if mime_data.hasFormat('text/plain'):
            # Accept the drag operation
            event.acceptProposedAction()
        else:
            # Ignore the drag operation
            event.ignore()

    def dragMoveEvent(self, event):
        # Get the mime data from the event
        mime_data = event.mimeData()
        # If the mime data contains text/plain data
        if mime_data.hasFormat('text/plain'):
            # Accept the drag operation
            event.acceptProposedAction()
        else:
            # Ignore the drag operation
            event.ignore()

    def dropEvent(self, event):
        # Get the mime data from the event
        mime_data = event.mimeData()
        # If the mime data contains text/plain data
        if mime_data.hasFormat('text/plain'):
            # Get the data as bytes and convert to string
            data = bytes(mime_data.data('text/plain')).decode()
            # Convert the string back to a list
            selected_data = [tag.strip() for tag in eval(data) if len(tag.strip()) > 0]

            if len(selected_data) > 0:
                # Get the tree node it dropped on
                current_item = self.itemAt(event.pos())
                # Calculate the full path from root to current node
                path = []
                while current_item is not None:
                    path.insert(0, current_item.text(0))
                    current_item = current_item.parent()
                full_path = '/'.join(path)

                df = self.update_tags_path(self.database, selected_data, full_path)

                self.on_operation_done(df, refresh_tree=False)

    def update_tags_path(self, df: pd.DataFrame, tags: [str], _path: str) -> pd.DataFrame or None:
        # Check if any of the tags already exist in the dataframe
        for tag in tags:
            if tag in df['tag'].values:
                df.loc[df['tag'] == tag, 'path'] = _path
            else:
                # Create a new row with the tags and path
                new_row = pd.DataFrame({'tag': tags, 'path': [_path] * len(tags)})
                # Append the new row to the dataframe
                df = df.append(new_row, ignore_index=True)
        return df
        
    def save_expand_items() -> list:
        # Save the expanded state of all items
        expanded_items = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.isExpanded():
                expanded_items.append(item.text(0))

    def restore_expand_items(expanded_items: list):
        # Restore the expanded state of all items
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.text(0) in expanded_items:
                item.setExpanded(True)


class CustomTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def mimeData(self, indexes):
        # Get the data from the first column of the selected rows
        selected_data = []
        for index in indexes:
            if index.column() == 0:
                selected_data.append(index.text())
        # Create a mime data object and set the data
        mime_data = QMimeData()
        mime_data.setData('text/plain', str(selected_data).encode())
        return mime_data


class AnalysisWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.positive_tags = []
        self.negative_tags = []
        self.extra_data = ''
        self.positive_df = pd.DataFrame(columns=DATABASE_FIELDS)
        self.negative_df = pd.DataFrame(columns=DATABASE_FIELDS)

        self.tag_database = load_tag_data()

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
        # Create the group widget for the positive table
        self.positive_group = QGroupBox("Positive", parent=self)
        # Create the multiple column table for the positive group
        self.positive_table = CustomTableWidget(parent=self)
        self.positive_table.setColumnCount(2)
        self.positive_table.setRowCount(5)
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
        # Create the tree widget for the tree group
        self.tree_group = QGroupBox("Tree", parent=self)
        # Create the tree widget for the tree group
        self.tree = DraggableTree(self.tag_database, self.on_edit_done, parent=self)
        # Create the tree widget for the tree group with one column and the specified name
        self.tree.setHeaderLabels(['Tag分类（Drag & Drop）'])
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
        root_layout.setStretch(1, 8)

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

        self.update_tag_path_tree()

    # Define a function to be called when the text in self.text_edit changes
    def on_prompt_edit(self):
        # Call parse_prompts with the input of self.text_edit
        self.positive_tags, self.negative_tags, self.extra_data = parse_prompts(self.text_edit.toPlainText())
        self.rebuild_analysis_table(True, True, True)

    # Define a function to be called when a cell in the positive table is double clicked
    def on_positive_table_double_click(self, row, column):
        self.do_edit_item(self.positive_table, row, self.positive_df)

    # Define a function to be called when a cell in the negative table is double clicked
    def on_negative_table_double_click(self, row, column):
        self.do_edit_item(self.negative_table, row, self.negative_df)

    def update_tag_path_tree(self):
        # Clear the tree
        self.tree.clear()

        # Get unique path values from tag_database
        unique_paths = unique_list(PRESET_TAG_PATH + list(self.tag_database['path'].unique()))

        # Loop through each unique path
        for path in unique_paths:
            if path.strip() == '':
                continue

            # Split the path into its individual parts
            parts = path.split('/')

            # Start at the root of the tree
            current_item = self.tree.invisibleRootItem()

            # Loop through each part of the path
            for part in parts:
                part = part.strip()
                if part == '':
                    continue

                # Check if the current part already exists as a child of the current item
                child_item = None
                for i in range(current_item.childCount()):
                    if current_item.child(i).text(0) == part:
                        child_item = current_item.child(i)
                        break

                # If the current part does not exist as a child of the current item, create a new item for it
                if child_item is None:
                    child_item = QTreeWidgetItem([part])
                    current_item.addChild(child_item)

                # Set the current item to be the child item for the next iteration of the loop
                current_item = child_item

    def do_edit_item(self, table: QTableWidget, row, df):
        item = self.positive_table.item(row, 0)
        if item is not None:
            # Get the tag from the selected row
            tag = table.item(row, 0).text()
            editor = DataFrameRowEditDialog(self.tag_database, DATABASE_SUPPORT_FIELD, 'tag', tag)
            result = editor.exec_()

            if result == QDialog.Accepted:
                self.on_edit_done()

    # ---------------------------------------------------------------------------------------------

    def on_edit_done(self, new_df: pd.DataFrame = None, refresh_table: bool = True, refresh_tree: bool = True):
        self.on_database_updated(new_df, refresh_tree)
        self.rebuild_analysis_table(True, True, refresh_table)

    def on_database_updated(self, new_df: pd.DataFrame = None, refresh_ui: bool = True):
        if new_df is not None:
            self.tag_database = new_df
            self.tree.database = new_df
        self.tag_database = self.tag_database.reindex().fillna('')
        self.save_database()
        if refresh_ui:
            self.update_tag_path_tree()

    def rebuild_analysis_table(self, positive: bool, negative: bool, refresh_ui: bool = True):
        # Based on positive_tags and negative_tags

        # Join positive_df with tag_database by 'tag' row. Keep all tag_database columns.
        # If the tag not in tag_database, the columns are empty string. The same to negative_df.

        if positive:
            positive_tag_data_dict = tags_list_to_tag_data(unique_list(self.positive_tags))
            if not self.tag_database.empty:
                self.positive_df = pd.DataFrame(positive_tag_data_dict)
                self.positive_df = merge_df_keeping_left_value(self.positive_df, self.tag_database, on='tag')
            else:
                self.positive_df = pd.DataFrame(positive_tag_data_dict, columns=DATABASE_FIELDS).fillna('')
            if refresh_ui:
                dataframe_to_table_widget(self.positive_table, self.positive_df, ANALYSIS_SHOW_COLUMNS, [])

        if negative:
            negative_tag_data_dict = tags_list_to_tag_data(unique_list(self.negative_tags))
            if not self.tag_database.empty:
                self.negative_df = pd.DataFrame(negative_tag_data_dict)
                self.negative_df = merge_df_keeping_left_value(self.negative_df, self.tag_database, on='tag')
            else:
                self.negative_df = pd.DataFrame(negative_tag_data_dict, columns=DATABASE_FIELDS).fillna('')
            if refresh_ui:
                dataframe_to_table_widget(self.negative_table, self.negative_df, ANALYSIS_SHOW_COLUMNS, [])

    def save_database(self):
        backup_file_safe(PUBLIC_DATABASE, BACKUP_LIMIT)
        backup_file_safe(PRIVATE_DATABASE, BACKUP_LIMIT)
        save_tag_data(self.tag_database)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.tabs = QTabWidget()
        self.analysis_tab = AnalysisWindow()
        self.generate_tab = QWidget()
        self.init_ui()

    def init_ui(self):
        self.tabs.addTab(self.analysis_tab, "Analysis")
        self.tabs.addTab(self.generate_tab, "Generate")
        self.setCentralWidget(self.tabs)
        self.resize(1280, 800)
        self.setWindowTitle('Stable Diffusion Tag 分析管理 - Sleepy')


def test_backup_file():
    for i in range(0, 20):
        backup_file('D:/A.csv', 10)
        time.sleep(1)


if __name__ == '__main__':
    # test_backup_file()
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
