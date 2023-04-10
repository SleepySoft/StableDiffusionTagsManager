import sys
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, \
    QGroupBox, QTableWidget, QTableWidgetItem


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
    if not {'tag', 'stance', 'path', 'value', 'label', 'translate_cn', 'comments', 'weight',
            'statistics'}.issubset(df_tags.columns):
        # Add the missing fields to df_tags
        df_tags = df_tags.reindex(columns=['tag', 'stance', 'path', 'value', 'label', 'translate_cn', 'comments', 'weight', 'statistics'])
    
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



class AnalysisWindow(QWidget):
    def __init__(self):
        super().__init__()
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
