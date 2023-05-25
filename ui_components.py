import math
from collections import OrderedDict
from functools import partial

import pandas as pd

from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QVBoxLayout, QTableWidget, QTableWidgetItem, QTreeWidget, QAbstractItemView, QDialog, \
    QPushButton, QDialogButtonBox, QTreeWidgetItem, QPlainTextEdit

from Prompts import try_float, WEIGHT_INC_BASE, WEIGHT_DEC_BASE
from TagManager import PRIMARY_KEY, TagManager
from app_utility import format_float
from df_utility import translate_df


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
            data_dict = eval(data)
            # Convert the string back to a list
            selected_data = [item[PRIMARY_KEY].strip() for item in data_dict if len(item[PRIMARY_KEY].strip()) > 0]

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


class TagViewTableWidget(QTableWidget):
    def __init__(self, data_columns: list, parent=None):
        super().__init__(parent)
        self.data_columns = data_columns
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def get_selected_row_field_value(self, column_index: int) -> [str]:
        selected_fields = [self.item(row.row(), column_index).text() for row in self.selectionModel().selectedRows()]
        return selected_fields

    def dragEnterEvent(self, event):
        event.ignore()

    def dragMoveEvent(self, event):
        event.ignore()

    def mimeData(self, indexes):
        # Get the data from the selected rows
        selected_data = []
        for index in indexes:
            if index.column() == 0:
                row_data = {}
                for column in range(self.columnCount()):
                    item = self.item(index.row(), column)
                    row_data[self.data_columns[column]] = item.text()
                selected_data.append(row_data)
        # Create a mime data object and set the data
        mime_data = QMimeData()
        mime_data.setData('text/plain', str(selected_data).encode())
        return mime_data

    # def mimeData(self, indexes):
    #     # Get the data from the first column of the selected rows
    #     selected_data = []
    #     for index in indexes:
    #         if index.column() == 0:
    #             item = self.item(index.row(), index.column())
    #             selected_data.append(item.text())
    #     # Create a mime data object and set the data
    #     mime_data = QMimeData()
    #     mime_data.setData('text/plain', str(selected_data).encode())
    #     return mime_data

    # startDrag方法的supportedActions参数是一个标志，它指定了拖放操作期间支持的操作。
    # 这些操作可以是Qt.CopyAction、Qt.MoveAction、Qt.LinkAction或它们的组合。
    # 例如，如果您希望拖放操作仅支持复制操作，则可以将supportedActions参数设置为Qt.CopyAction。
    #
    # 在之前给您提供的示例代码中，我们没有使用supportedActions参数，而是直接在调用exec_方法时将默认操作设置为Qt.CopyAction。
    # 这样，无论拖放操作期间支持哪些操作，都会使用复制操作作为默认操作，从而防止删除表格中的数据。

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        drag.setMimeData(self.mimeData(self.selectedIndexes()))
        # Set the default action to CopyAction to prevent deleting the data
        drag.exec_(Qt.CopyAction)

    def dropEvent(self, event):
        event.ignore()


class TagEditTableWidget(QTableWidget):
    def __init__(self, tag_manager: TagManager, fields: OrderedDict, *args, **kwargs):
        super(TagEditTableWidget, self).__init__(*args, **kwargs)

        self.tag_manager = tag_manager
        self.filed_declare = fields
        self.table_editing_data = pd.DataFrame(columns=list(fields.keys()))

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropOverwriteMode(False)

        self.setColumnCount(len(fields) + 2)
        self.setHorizontalHeaderLabels(list(fields.values()) + ['', ''])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            rows = sorted(set(item.row() for item in self.selectedItems()))
            # Remove the row from the dataframe
            self.table_editing_data.drop(index=rows, inplace=True)
            self.table_editing_data.reset_index(drop=True, inplace=True)
            self.update_table()

            event.accept()
        else:
            super().keyPressEvent(event)

    def dropEvent(self, event):
        if event.source() == self:
            # Internal move
            rows = sorted(set(item.row() for item in self.selectedItems()))
            target_row = self.indexAt(event.pos()).row()
            if target_row == -1:
                target_row = self.rowCount()
            for row in reversed(rows):
                source_row_adjusted = row + 1 if row > target_row else row
                if row < target_row:
                    target_row += 1
                self.insertRow(target_row)
                for col in range(self.columnCount()):
                    self.setItem(target_row, col, self.takeItem(source_row_adjusted, col))
                self.removeRow(source_row_adjusted)
            self.adjust_order()
            event.accept()
        else:
            # External drop

            data = event.mimeData().data('text/plain').data().decode()
            tag_data = eval(data)

            append_rows = []
            for data in tag_data:
                tag = data[PRIMARY_KEY]
                weight = data.get('weight', '')

                # weight_digit = try_float(weight)
                # if weight_digit is None:
                #     weight_log = 0
                # else:
                #     weight_log = math.log(weight_digit, 1.1) if weight_digit > 1 else math.log(weight_digit, 0.9)

                # TODO: Dynamic
                if not self.table_editing_data[PRIMARY_KEY].isin([tag]).any():
                    # trans = self.tag_manager.get_property(tag, 'translate_cn')
                    append_rows.append([tag, weight, ''] + [''] * (len(self.filed_declare) - 3))

            self.table_editing_data = self.table_editing_data.append(
                pd.DataFrame(append_rows, columns=self.table_editing_data.columns))
            self.table_editing_data = self.table_editing_data.reset_index(drop=True)
            translate_df(self.table_editing_data, PRIMARY_KEY, 'translate_cn', True, True)
            event.accept()
        self.update_table()

    def dragEnterEvent(self, event):
        if event.source() == self:
            event.accept()
        else:
            data = event.mimeData().data('text/plain').data().decode()
            if data.startswith('[') and data.endswith(']'):
                event.accept()
            else:
                event.ignore()

    def dragMoveEvent(self, event):
        if event.source() == self:
            event.accept()
        else:
            data = event.mimeData().data('text/plain').data().decode()
            if data.startswith('[') and data.endswith(']'):
                event.accept()
            else:
                event.ignore()

    def mimeData(self, indexes):
        # Get the data from the first column of the selected rows
        selected_data = []
        for index in indexes:
            if index is None:
                pass
            elif index.column() == 0:
                item = self.item(index.row(), index.column())
                selected_data.append(item.text())
        # Create a mime data object and set the data
        mime_data = QMimeData()
        mime_data.setData('text/plain', str(selected_data).encode())
        return mime_data

    def mimeTypes(self):
        return ['text/plain']

    # --------------------------------------------------------------------------------------------

    def get_selected_row_data(self, column_index):
        selected_rows = self.selectionModel().selectedRows()
        selected_data = []
        for index in selected_rows:
            if index is None:
                pass
            else:
                item = self.item(index.row(), column_index)
                selected_data.append(item.text())
        return selected_data

    def set_data_by_selected_row(self, column_index, data):
        selected_rows = self.selectionModel().selectedRows()
        for index in selected_rows:
            if index is None:
                pass
            else:
                item = self.item(index.row(), column_index)
                item.setText(data)
                tag_item = self.item(index.row(), 0)
                tag = tag_item.text()
                column_name = self.table_editing_data.columns[column_index]
                self.table_editing_data.loc[self.table_editing_data[PRIMARY_KEY] == tag, column_name] = data

    def generate(self, file_name: str, wildcards_path: str):
        df_flat_tags = self.table_editing_data[
            self.table_editing_data['shuffle'].isnull() | (self.table_editing_data['shuffle'] == '')]
        df_wildcards = self.table_editing_data[
            self.table_editing_data['shuffle'].notnull() & (self.table_editing_data['shuffle'] != '')]

        wildcards = []
        for shuffle, group in df_wildcards.groupby('shuffle'):
            tags = ', '.join(group['tag'])
            wildcards_file_name = f"{wildcards_path}/{shuffle}.txt"
            with open(wildcards_file_name, 'w') as f:
                f.write(tags)
            wildcards.append(f"__{shuffle}__")

        flat_tags = []
        for index, row in df_flat_tags.iterrows():
            tag = row['tag']
            weight = row['weight']

            if try_float(weight):
                tag = '(%s: %s)' % (tag, weight)

            # # If the weight is 1, than it's (tag), if 2 than ((tag)) and so on.
            # if weight > 0:
            #     tag = f"{'(' * weight}{tag}{')' * weight}"
            # elif weight < 0:
            #     tag = f"{'[' * abs(weight)}{tag}{']' * abs(weight)}"

            flat_tags.append(tag)

        with open(file_name, 'w') as f:
            f.write(', '.join(wildcards + flat_tags))

    # --------------------------------------------------------------------------------------------

    def handle_button_click(self, operation, row):
        tag_item = self.item(row, 0)
        tag = tag_item.text()

        # Add the weight field by 1 if the PRIMARY_KEY field equals to tag
        if PRIMARY_KEY in self.table_editing_data.columns:
            # Pass the tag to handling function with partial
            # Handle '+' button click
            if operation == '+':
                weight = self.table_editing_data.loc[self.table_editing_data[PRIMARY_KEY] == tag, 'weight']
                weight_digit = try_float(weight)
                if weight_digit is not None:
                    weight_digit += 0.1
                else:
                    weight_digit = 1.1
                self.table_editing_data.loc[self.table_editing_data[PRIMARY_KEY] == tag, 'weight'] = weight_digit
            elif operation == '-':
                weight = self.table_editing_data.loc[self.table_editing_data[PRIMARY_KEY] == tag, 'weight']
                weight_digit = try_float(weight)
                if weight_digit is not None:
                    weight_digit -= 0.1
                else:
                    weight_digit = 0.9
                self.table_editing_data.loc[self.table_editing_data[PRIMARY_KEY] == tag, 'weight'] = weight_digit
            else:
                raise ValueError(f'Invalid operation: {operation}')
            self.update_row_weight(row)

    def adjust_order(self):
        # Get the first column of table itself as tag list
        tag_list = []
        for row in range(self.rowCount()):
            tag_item = self.item(row, 0)
            tag = tag_item.text()
            tag_list.append(tag)
        # Sort the self.table_editing_data by PRIMARY_KEY column in tag list order
        self.table_editing_data = self.table_editing_data.set_index(PRIMARY_KEY).loc[tag_list].reset_index()

    def update_table(self):
        TagManager.dataframe_to_table_widget(
            self, self.table_editing_data, self.filed_declare, ['', ''])  # , self.df_to_table_decorator)

        for row in range(self.rowCount()):
            plus_button = QPushButton('+')
            minus_button = QPushButton('-')

            plus_button.clicked.connect(partial(self.handle_button_click, '+', row))
            minus_button.clicked.connect(partial(self.handle_button_click, '-', row))

            plus_button.setMinimumSize(0, 0)
            minus_button.setMinimumSize(0, 0)

            plus_button.setStyleSheet("QPushButton {padding: 0px; margin: 0px; font-size: 12px;}")
            minus_button.setStyleSheet("QPushButton {padding: 0px; margin: 0px; font-size: 12px;}")

            self.setCellWidget(row, len(self.filed_declare) + 1, plus_button)
            self.setCellWidget(row, len(self.filed_declare), minus_button)

            self.resizeColumnToContents(1)
            self.resizeColumnToContents(len(self.filed_declare))
            self.resizeColumnToContents(len(self.filed_declare) + 1)

    # def df_to_table_decorator(self, row, col, item: QTableWidgetItem):
    #     if col == 1:
    #         tag_item = self.item(row, 0)
    #         tag = tag_item.text()
    #         # Find the weight value in dataframe by tag field
    #         weight_value = int(
    #             self.table_editing_data.loc[self.table_editing_data[PRIMARY_KEY] == tag, 'weight'].values[0])
    #         # Format the new_value to a string with 2 decimal places
    #         weight_value_str = self.format_weight(weight_value)
    #         # Update the weight value to col 2 of table row
    #         item.setText(weight_value_str)
    #     else:
    #         pass

    def update_row_weight(self, row):
        tag_item = self.item(row, 0)
        tag = tag_item.text()
        # Find the weight value in dataframe by tag field
        weight_value = self.table_editing_data.loc[self.table_editing_data[PRIMARY_KEY] == tag, 'weight'].values[0]
        weight_value_str = format_float(weight_value)
        # Update the weight value to col 2 of table row
        weight_item = QTableWidgetItem(str(weight_value_str))
        self.setItem(row, 1, weight_item)

    # def format_weight(self, weight_level: int) -> str:
    #     if weight_level >= 0:
    #         weight_value = WEIGHT_INC_BASE ** weight_level
    #     else:
    #         weight_value = WEIGHT_DEC_BASE ** abs(weight_level)
    #     return '{:.2f}'.format(weight_value)


class CustomPlainTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dropEvent(self, event):
        # Get the drop data
        mime_data = event.mimeData()
        if mime_data.hasFormat('text/plain'):
            # Get the data as bytes and convert to string
            data = bytes(mime_data.data('text/plain')).decode()
            # Convert the string back to a list
            selected_data = [tag.strip() for tag in eval(data) if len(tag.strip()) > 0]
            # Join the values with a comma separator and set the text
            tags_text = ', '.join(selected_data)

            current_text = self.toPlainText().rstrip()
            if len(current_text) > 0 and current_text[-1] != ',':
                # Add a comma and the new text
                new_text = current_text + ', ' + tags_text
            else:
                # Add the new text
                new_text = current_text + tags_text
            # Set the new text
            self.setPlainText(new_text)

            event.acceptProposedAction()
