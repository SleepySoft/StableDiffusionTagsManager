import re
import sys
import pandas as pd
from collections import OrderedDict

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QDataStream
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDialog, QPushButton, \
    QDialogButtonBox

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

PRESET_TAG_PATH = ['通用正向', '通用反向',
                   '场景/室外', '场景/室内', '场景/幻境',
                   '脸部/头发', '脸部/眼睛', '脸部/嘴巴',
                   '衣服', '动作', '特效', '18x']


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


def merge_df_keeping_left_value(left: pd.DataFrame, right: pd.DataFrame, on: str):
    df = left.merge(right, on=on, how='left', suffixes=('', '_y'))
    df = df.drop([col for col in df.columns if col.endswith('_y')], axis=1)
    df = df.fillna('')
    return df


def load_tag_data():
    # Load public.csv to df_public if it exists
    try:
        df_public = pd.read_csv('public.csv')
    except FileNotFoundError:
        df_public = pd.DataFrame(columns=['tag'])

    # Load private.csv to df_private if it exists
    try:
        df_private = pd.read_csv('private.csv')
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
    df_private.to_csv('private.csv', index=False)
    df_public.to_csv('public.csv', index=False)


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
        if parts[1].isdigit():
            # If the second part is a number, set the raw_tag and tag_weight accordingly
            raw_tag = parts[0]
            tag_weight = int(parts[1])
        else:
            # If the second part is not a number, set the raw_tag to the entire tag and tag_weight to 1
            raw_tag = tag
            tag_weight = 1.0
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


def tags_list_to_tag_data(tags: [str]):
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
            data_weight[index] = float(data_weight[index]) * float(tag_weight)
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
        for col, field in enumerate(extra_headers, start=len(field_mapping)):
            item = QTableWidgetItem('')
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
    def __init__(self, database: pd.DataFrame, on_database_update, parent=None):
        super().__init__(parent)
        self.database = database
        self.on_database_update = on_database_update
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

                self.update_tags_path(self.database, selected_data, full_path)
                self.on_database_update()

    def update_tags_path(self, df: pd.DataFrame, tags: [str], _path: str):
        # If the tags are new?
        self.database.loc[self.database['tag'].isin(tags), 'path'] = _path


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
        # Add the reserved area to the top layout
        reserved_area = QWidget()
        top_layout.addWidget(reserved_area, 7)
        # Set the space ratio to 70% and 30%
        top_layout.setStretch(0, 7)
        top_layout.setStretch(1, 3)
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
        self.tree = DraggableTree(self.tag_database, self.on_database_updated, parent=self)
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

        positive_tag_data = tags_list_to_tag_data(unique_list(self.positive_tags))
        negative_tag_data = tags_list_to_tag_data(unique_list(self.negative_tags))

        # Join positive_df with tag_database by 'tag' row. Keep all tag_database columns.
        # If the tag not in tag_database, the columns are empty string. The same to negative_df.
        if not self.tag_database.empty:
            self.positive_df = pd.DataFrame(positive_tag_data)
            self.negative_df = pd.DataFrame(negative_tag_data)
            self.positive_df = merge_df_keeping_left_value(self.positive_df, self.tag_database, on='tag')
            self.negative_df = merge_df_keeping_left_value(self.negative_df, self.tag_database, on='tag')
        else:
            self.positive_df = pd.DataFrame(positive_tag_data, columns=DATABASE_FIELDS).fillna('')
            self.negative_df = pd.DataFrame(negative_tag_data, columns=DATABASE_FIELDS).fillna('')

        dataframe_to_table_widget(self.positive_table, self.positive_df, ANALYSIS_SHOW_COLUMNS, [])
        dataframe_to_table_widget(self.negative_table, self.negative_df, ANALYSIS_SHOW_COLUMNS, [])

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
                self.on_database_updated()
                self.update_tag_path_tree()
                dataframe_to_table_widget(table, df, ANALYSIS_SHOW_COLUMNS, [])

    def on_database_updated(self):
        self.tag_database = self.tag_database.reindex().fillna('')
        self.save_database()

    def save_database(self):
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
