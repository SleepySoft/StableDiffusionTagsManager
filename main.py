import sys
import pandas as pd
from collections import OrderedDict

from PyQt5.QtCore import Qt, QDataStream
from PyQt5.QtCore import QMimeData
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QDialog, QPushButton, \
    QDialogButtonBox

DATABASE_FIELDS = ['tag', 'stance', 'path', 'value', 'label', 'translate_cn', 'comments', 'weight', 'statistics']

ANALYSIS_COLUMNS = OrderedDict([
    ('Tag', 'tag'),
    ('Group', 'path'),
    ('Value', 'value'),
    ('Bookmark', 'label'),
    ('Name', 'translate_cn'),
    ('Comments', 'comments')
])

ANALYSIS_COL2FIELD = list(ANALYSIS_COLUMNS.values())


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
    df_tags = pd.merge(df_public, df_private, on='tag', how='outer')

    # Check if any of the required fields are missing in df_tags
    if not set(DATABASE_FIELDS).issubset(df_tags.columns):
        # Add the missing fields to df_tags
        df_tags = df_tags.reindex(columns=DATABASE_FIELDS)

    # Replace NaN or null values with empty strings
    df_tags = df_tags.fillna('')

    # Return the resulting DataFrame
    return df_tags


def parse_tags(prompt_text: str):
    # Split the prompt_text by '\n' and strip each line, remove empty lines
    lines = [line.strip() for line in prompt_text.split('\n') if line.strip()]

    # If line 0 exists and there's a ':' before any ',', remove the sub string before ':' and ':' it self
    if lines and ':' in lines[0] and ',' in lines[0][lines[0].index(':'):]:
        lines[0] = lines[0][lines[0].index(':') + 1:]

    # If line 1 exists and there's a ':' before any ',', remove the sub string before ':' and ':' it self
    if len(lines) > 1 and ':' in lines[1] and ',' in lines[1][lines[1].index(':'):]:
        lines[1] = lines[1][lines[1].index(':') + 1:]

    # Split line 0 by ',' and strip each sub string. line 0 is positive_tags, line 1 is negitive_tags.
    positive_tags = [tag.strip() for tag in lines[0].split(',')] if lines else []
    negative_tags = [tag.strip() for tag in lines[1].split(',')] if len(lines) > 1 else []

    # Join the rest lines by '\n' as extra_data. If no more lines extra_data should be empty string.
    extra_data = '\n'.join(lines[2:]) if len(lines) > 2 else ''

    # Return positive_tags, negitive_tags, extra_data
    return positive_tags, negative_tags, extra_data


def dataframe_to_table_widget(
        table_widget: QTableWidget, dataframe: pd.DataFrame,
        field_mapping: OrderedDict, extra_fields: [str]):

    # Clear the table
    table_widget.clear()
    table_widget.setRowCount(0)

    # Set the column count for the table
    table_widget.setColumnCount(len(field_mapping) + len(extra_fields))

    # Set the horizontal header labels for the table
    header_labels = [field.capitalize() for field in field_mapping.keys()] + extra_fields
    table_widget.setHorizontalHeaderLabels(header_labels)

    # Set the row count for the table
    table_widget.setRowCount(len(dataframe))

    # Fill the table with data from the dataframe
    for row in range(len(dataframe)):
        for col, field in enumerate(field_mapping.values()):
            item = QTableWidgetItem(str(dataframe.loc[row, field]))
            table_widget.setItem(row, col, item)
        for col, field in enumerate(extra_fields, start=len(field_mapping)):
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
            if field in field_name_mapping:
                display_name = field_name_mapping[field]
            else:
                display_name = field
            item = QTableWidgetItem(display_name)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setData(0, field)
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
            field_name = field_item.data(0)
            if field_item and value_item:
                data[field_name] = value_item.text().strip()

        if (df[self.unique_field] == self.unique_field_value).any():
            df.loc[df[self.unique_field] == self.unique_field_value] = data
        else:
            df.loc[len(df)] = data

        # Call the base accept method to close the dialog
        super().accept()


class DraggableTree(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def dropEvent(self, event):
        if event.source() == self:
            super().dropEvent(event)
        else:
            data = event.mimeData()
            if data.hasFormat('application/x-qabstractitemmodeldatalist'):
                ba = data.data('application/x-qabstractitemmodeldatalist')
                ds = QDataStream(ba)
                while not ds.atEnd():
                    row = ds.readInt32()
                    column = ds.readInt32()
                    map_items = ds.readQVariantMap()
                    print(map_items)


class AnalysisWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.positive_tags = []
        self.negative_tags = []
        self.extra_data = ''
        self.positive_df = pd.DataFrame(columns=DATABASE_FIELDS)
        self.negative_df = pd.DataFrame(columns=DATABASE_FIELDS)

        self.tag_database = pd.DataFrame(columns=DATABASE_FIELDS)

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
        self.positive_table = QTableWidget(parent=self)
        self.positive_table.setColumnCount(2)
        self.positive_table.setRowCount(5)
        positive_group_layout = QVBoxLayout()
        positive_group_layout.addWidget(self.positive_table)
        self.positive_group.setLayout(positive_group_layout)
        # Create the group widget for the negative table
        self.negative_group = QGroupBox("Negative", parent=self)
        # Create the multiple column table for the negative group
        self.negative_table = QTableWidget(parent=self)
        self.negative_table.setColumnCount(2)
        self.negative_table.setRowCount(5)
        negative_group_layout = QVBoxLayout()
        negative_group_layout.addWidget(self.negative_table)
        self.negative_group.setLayout(negative_group_layout)
        # Create the tree widget for the tree group
        self.tree_group = QGroupBox("Tree", parent=self)
        # Create the tree widget for the tree group
        self.tree = DraggableTree(parent=self)
        self.tree.setHeaderHidden(True)
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

        self.resize(1024, 768)

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

        # # Test
        # # Loop through 10 times to add 10 items to the tree under its root
        # for i in range(10):
        #     # Create a new item with the text "Item {i+1}"
        #     new_item = QTreeWidgetItem(["Item {}".format(i+1)])
        #     # Add the new item to the tree under its root
        #     self.tree.addTopLevelItem(new_item)

    # Define a function to be called when the text in self.text_edit changes
    def on_prompt_edit(self):
        # Call parse_tags with the input of self.text_edit
        self.positive_tags, self.negative_tags, self.extra_data = parse_tags(self.text_edit.toPlainText())

        # Create a pandas dataframe for the positive tags
        self.positive_df = pd.DataFrame({'tag': self.positive_tags})

        # Create a pandas dataframe for the negative tags
        self.negative_df = pd.DataFrame({'tag': self.negative_tags})

        # Join positive_df with tag_database by 'tag' row. Keep all tag_database columns.
        # If the tag not in tag_database, the columns are empty string. The same to negative_df.
        if self.positive_df.empty:
            self.positive_df = pd.DataFrame(columns=DATABASE_FIELDS)
        else:
            self.positive_df = self.positive_df.merge(self.tag_database, on='tag', how='left').fillna('')

        if self.negative_df.empty:
            self.negative_df = pd.DataFrame(columns=DATABASE_FIELDS)
        else:
            self.negative_df = self.negative_df.merge(self.tag_database, on='tag', how='left').fillna('')

        dataframe_to_table_widget(self.positive_table, self.positive_df, ANALYSIS_COLUMNS, [])
        dataframe_to_table_widget(self.negative_table, self.negative_df, ANALYSIS_COLUMNS, [])

    # Define a function to be called when a cell in the positive table is double clicked
    def on_positive_table_double_click(self, row, column):
        # Get the tag from the selected row
        item = self.positive_table.item(row, 0)
        if item is not None:
            tag = item.text()
            editor = DataFrameRowEditDialog(self.tag_database, {}, 'tag', tag)
            result = editor.exec_()

            if result == QDialog.Accepted:
                dataframe_to_table_widget(self.positive_table, self.positive_df, ANALYSIS_COLUMNS, [])
                dataframe_to_table_widget(self.negative_table, self.negative_df, ANALYSIS_COLUMNS, [])
                self.update_tag_path_tree()

    # Define a function to be called when a cell in the negative table is double clicked
    def on_negative_table_double_click(self, row, column):
        # Get the tag from the selected row
        tag = self.negative_table.item(row, 0).text()
        editor = DataFrameRowEditDialog(self.tag_database, {}, 'tag', tag)
        editor.exec_()

    def update_tag_path_tree(self):
        # Clear the tree
        self.tree.clear()

        # Get unique path values from tag_database
        unique_paths = self.tag_database['path'].unique()

        # Loop through each unique path
        for path in unique_paths:
            # Split the path into its individual parts
            parts = path.split('/')

            # Start at the root of the tree
            current_item = self.tree.invisibleRootItem()

            # Loop through each part of the path
            for part in parts:
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
