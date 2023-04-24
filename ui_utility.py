import pandas as pd

from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtWidgets import QVBoxLayout, QTableWidget, QTableWidgetItem, QTreeWidget, QAbstractItemView, QDialog, \
    QPushButton, QDialogButtonBox, QTreeWidgetItem

from TagManager import PRIMARY_KEY


class DataFrameRowEditDialog(QDialog):
    def __init__(self, df: pd.DataFrame, field_name_mapping: dict, edit_row_data: pd.DataFrame, unique_field: str):
        super().__init__()

        self.database = df
        self.unique_field = unique_field
        self.unique_field_value = ''

        # Create the editable table widget
        self.table_widget = QTableWidget(len(df.columns), 2, parent=self)

        # Set the horizontal header labels for the table
        header_labels = ['Field', 'Value']
        self.table_widget.setHorizontalHeaderLabels(header_labels)

        # Fill the table with data from the row
        # Update table fields based on main dataframe's fields
        for row_idx, field in enumerate(df.columns):
            if field in field_name_mapping.keys():
                display_name = field_name_mapping[field]
            else:
                display_name = field
            item = QTableWidgetItem(display_name)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setData(Qt.UserRole, field)
            self.table_widget.setItem(row_idx, 0, item)

            if edit_row_data is not None and not edit_row_data.empty and field in edit_row_data.columns:
                # If the edit_row_data is not empty and unique_field is not empty -> Edit mode
                # Get the first row of the filtered dataframe
                item = QTableWidgetItem(edit_row_data.iloc[0][field])
                if field == unique_field:
                    self.unique_field_value = edit_row_data.iloc[0][unique_field]
                    if self.unique_field_value.strip() != '':
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            else:
                # If not -> Append mode. The unique_field is editable
                item = QTableWidgetItem(str(''))
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
            field_name = field_item.data(Qt.UserRole)
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

    def get_node_path(self, item: QTreeWidgetItem) -> str:
        # Calculate the full path from root to current node
        path = []
        while item is not None:
            path.insert(0, item.text(0))
            item = item.parent()
        full_path = '/'.join(path)
        return full_path

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
                full_path = self.get_node_path(current_item)

                df = self.update_tags_path(self.database, selected_data, full_path)
                self.on_operation_done(df, refresh_tree=False)

    def update_tags_path(self, df: pd.DataFrame, tags: [str], _path: str) -> pd.DataFrame or None:
        # Check if any of the tags already exist in the dataframe
        for tag in tags:
            if tag in df[PRIMARY_KEY].values:
                df.loc[df[PRIMARY_KEY] == tag, 'path'] = _path
            else:
                # Create a new row with the tags and path
                new_row = pd.DataFrame({PRIMARY_KEY: [tag], 'path': [_path]})
                # Append the new row to the dataframe
                df = df.append(new_row, ignore_index=True)
        return df

    def save_expand_items(self) -> list:
        # Save the expanded state of all items
        expanded_items = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.isExpanded():
                expanded_items.append(item.text(0))

    def restore_expand_items(self, expanded_items: list):
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
