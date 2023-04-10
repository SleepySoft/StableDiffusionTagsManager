import sys
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem


FIELDS = ['tag', 'stance', 'path', 'value', 'label', 'translate_cn', 'comments', 'weight', 'statistics']
from collections import OrderedDict

COLUMNS = OrderedDict([
    ('Tag', 'tag'),
    ('Group', 'path'),
    ('Value', 'value'),
    ('Bookmark', 'label'),
    ('Name', 'translate_cn'),
    ('Comments', 'comments')
])


COL2FIELD = list(COLUMNS.values())


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
    if not set(FIELDS).issubset(df_tags.columns):
        # Add the missing fields to df_tags
        df_tags = df_tags.reindex(columns=FIELDS)
    
    # Replace NaN or null values with empty strings
    df_tags = df_tags.fillna('')
    
    # Return the resulting DataFrame
    return df_tags


def parse_tags(prompt_text: str):
    # Split the prompt_text by '\n' and strip each line, remove empty lines
    lines = [line.strip() for line in prompt_text.split('\n') if line.strip()]
    
    # If line 0 exists and there's a ':' before any ',', remove the sub string before ':' and ':' it self
    if lines and ':' in lines[0] and ',' in lines[0][lines[0].index(':'):]:
        lines[0] = lines[0][lines[0].index(':')+1:]
    
    # If line 1 exists and there's a ':' before any ',', remove the sub string before ':' and ':' it self
    if len(lines) > 1 and ':' in lines[1] and ',' in lines[1][lines[1].index(':'):]:
        lines[1] = lines[1][lines[1].index(':')+1:]
    
    # Split line 0 by ',' and strip each sub string. line 0 is positive_tags, line 1 is negitive_tags.
    positive_tags = [tag.strip() for tag in lines[0].split(',')] if lines else []
    negative_tags = [tag.strip() for tag in lines[1].split(',')] if len(lines) > 1 else []
    
    # Join the rest lines by '\n' as extra_data. If no more lines extra_data should be empty string.
    extra_data = '\n'.join(lines[2:]) if len(lines) > 2 else ''
    
    # Return positive_tags, negitive_tags, extra_data
    return positive_tags, negative_tags, extra_data


def dataframe_to_table(
    table_widget: QTableWidget, dataframe: pd.DataFrame, 
    field_mapping: OrderedDict, extra_fields: List[str]):
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



class AnalysisWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.tag_database = pd.DataFrame(columns=['tag'])

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
        # Create the bottom horizontal layout
        bottom_layout = QHBoxLayout()
        # Add the positive group to the bottom layout
        bottom_layout.addWidget(self.positive_group)
        # Add the negative group to the bottom layout
        bottom_layout.addWidget(self.negative_group)
        # Set the space ratio to 1:1
        bottom_layout.setStretch(0, 1)
        bottom_layout.setStretch(1, 1)
        # Add the bottom layout to the root layout
        root_layout.addLayout(bottom_layout)
        
        # Connect the on_prompt_edit function to the textChanged signal of self.text_edit
        self.text_edit.textChanged.connect(self.on_prompt_edit)

    # Define a function to be called when the text in self.text_edit changes
    def on_prompt_edit(self):
        # Call parse_tags with the input of self.text_edit
        positive_tags, negative_tags, extra_data = parse_tags(self.text_edit.toPlainText())

        # Update positive_tags to positive_table
        self.positive_table.setRowCount(len(positive_tags))
        for i, tag in enumerate(positive_tags):
            self.positive_table.setItem(i, 0, QTableWidgetItem(tag))

        # Update negitive_tags to negative_table
        self.negative_table.setRowCount(len(negative_tags))
        for i, tag in enumerate(negative_tags):
            self.negative_table.setItem(i, 0, QTableWidgetItem(tag))
  
    # def on_button_edit(self, table_widget: QTableWidget, edit_row: int):
    #     # Get data from the table and update to self.tag_database
    #     for col, field in enumerate(COL2FIELD.values()):
    #         item = table_widget.item(edit_row, col)
    #         if item is not None:
    #             value = item.text()
    #             key = table_widget.item(edit_row, 0).text()
    #             if key in self.tag_database.index:
    #                 self.tag_database.loc[key, field] = value
    #             else:
    #                 new_row = pd.Series({field: value}, name=key)
    #                 self.tag_database = self.tag_database.append(new_row)

    #     # Update the positive and negative tables
    #     self.update_tables()

    # def update_tables(self):
    #     # Update positive_tags to positive_table
    #     positive_tags = self.tag_database[self.tag_database['tag'] == 1]['tag'].tolist()
    #     self.positive_table.setRowCount(len(positive_tags))
    #     for i, tag in enumerate(positive_tags):
    #         self.positive_table.setItem(i, 0, QTableWidgetItem(tag))

    #     # Update negitive_tags to negative_table
    #     negative_tags = self.tag_database[self.tag_database['tag'] == 0]['tag'].tolist()
    #     self.negative_table.setRowCount(len(negative_tags))
    #     for i, tag in enumerate(negative_tags):
    #         self.negative_table.setItem(i, 0, QTableWidgetItem(tag))




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
