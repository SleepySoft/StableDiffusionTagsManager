import re
import pandas as pd
from collections import OrderedDict

from app_utility import *


PRIMARY_KEY = 'tag'

DATABASE_SUPPORT_FIELD = OrderedDict([
    (PRIMARY_KEY, '标签'),
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


class TagManager:
    def __init__(self, public_db: str, private_db: str, backup_limit: int):
        self.__public_db = public_db
        self.__private_db = private_db
        self.__database_observers = []
        self.__backup_limit = backup_limit
        self.__tag_database = TagManager.load_tag_data(public_db, private_db)
        self.__verify_database()

    def get_database(self) -> pd.DataFrame:
        return self.__tag_database

    def save_database(self):
        backup_file_safe(self.__public_db, self.__backup_limit)
        backup_file_safe(self.__private_db, self.__backup_limit)
        TagManager.save_tag_data(self.__tag_database, self.__public_db, self.__private_db)

    def inform_database_modified(self, new_df: pd.DataFrame, save: bool):
        if new_df is not None:
            self.__tag_database = new_df
        self.__tag_database = self.__tag_database.reindex().fillna('')
        self.__verify_database()
        if save:
            self.save_database()
        for ob in self.__database_observers:
            ob.on_database_changed()

    def register_database_observer(self, ob):
        """
        The observer should support following functions:
            def on_database_changed()
        :param ob: Observer
        :return:
        """
        self.__database_observers.append(ob)

    def get_property(self, primary_key: str, field: str) -> str:
        """
        Get the value of a field for a given primary key from the tag database.
        If the primary key is not found, return an empty string.
        :param primary_key: str
        :param field: str
        :return: str
        """
        try:
            return self.__tag_database.loc[self.__tag_database[PRIMARY_KEY] == primary_key, field].values[0]
        except IndexError:
            return ''

    # ------------------------------------------------------------------------------------------------------------------

    def __verify_database(self):
        duplicates = self.__tag_database.duplicated(subset=[PRIMARY_KEY], keep='first')
        duplicate_rows = self.__tag_database[duplicates]
        if len(duplicate_rows) > 0:
            print('Warning: Duplicate row found.')
            print(duplicate_rows)
            self.__tag_database = self.__tag_database.drop_duplicates(subset=[PRIMARY_KEY], keep='first')
        self.__tag_database = self.__tag_database.reset_index()

    # ------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def load_tag_data(public_db: str, private_db: str) -> pd.DataFrame:
        # Load public.csv to df_public if it exists
        try:
            df_public = pd.read_csv(public_db)
        except FileNotFoundError:
            df_public = pd.DataFrame(columns=[PRIMARY_KEY])

        # Load private.csv to df_private if it exists
        try:
            df_private = pd.read_csv(private_db)
        except FileNotFoundError:
            df_private = pd.DataFrame(columns=[PRIMARY_KEY])

        # Join df_public and df_private by field "tag" to create df_tags
        df_tags = pd.concat([df_public, df_private])

        # Check if any of the required fields are missing in df_tags
        if not set(DATABASE_FIELDS).issubset(df_tags.columns):
            # Add the missing fields to df_tags
            df_tags = df_tags.reindex(columns=DATABASE_FIELDS)

        # Replace NaN or null values with empty strings
        df_tags = df_tags.fillna('')
        df_tags = df_tags.reindex()

        return df_tags

    @staticmethod
    def save_tag_data(df: pd.DataFrame, public_db: str, private_db: str):
        # Split the dataframe into two based on the value of the 'private' field
        df_private = df[df['private'] == 'Y']
        df_public = df[df['private'] != 'Y']

        # Save the private and public dataframes to separate CSV files
        df_public.to_csv(public_db, index=False, encoding='utf-8')
        df_private.to_csv(private_db, index=False, encoding='utf-8')

    @staticmethod
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

    @staticmethod
    def analysis_tag(tag: str) -> (str, str):
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

    @staticmethod
    def tags_list_to_tag_data(tags: [str]) -> dict:
        data_tag = []
        data_weight = []
        for tag in tags:
            raw_tag, tag_weight = TagManager.analysis_tag(tag)
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
            PRIMARY_KEY: data_tag,
            'weight': data_weight
        }

    @staticmethod
    def dataframe_to_table_widget(
            table_widget, dataframe: pd.DataFrame,
            field_mapping: OrderedDict, extra_headers: [str],
            item_decorator: callable = None):

        from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem

        table_widget: QTableWidget

        # Backup sort information
        sort_column = table_widget.horizontalHeader().sortIndicatorSection()
        sort_order = table_widget.horizontalHeader().sortIndicatorOrder()

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

        try:
            # Fill the table with data from the dataframe
            for row in range(len(dataframe)):
                for col, field in enumerate(field_mapping.keys()):
                    item_text = str(dataframe.loc[row, field])
                    # print(item_text, end=' ')
                    item = QTableWidgetItem(item_text)

                    if item_decorator is not None:
                        item_decorator(row, col, item)

                    table_widget.setItem(row, col, item)
                # print('')
        except Exception as e:
            print(e)

        # Restore / Keep sort after data update.
        table_widget.sortByColumn(sort_column, sort_order)

    @staticmethod
    def update_tag_path_tree(tree_widget, dataframe: pd.DataFrame, preset_path: list):
        from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

        tree_widget: QTreeWidget

        # Clear the tree
        tree_widget.clear()

        # Get unique path values from tag_database
        unique_paths = unique_list(preset_path + list(dataframe['path'].unique()))

        # Loop through each unique path
        for path in unique_paths:
            if path.strip() == '':
                continue

            # Split the path into its individual parts
            parts = path.split('/')

            # Start at the root of the tree
            current_item = tree_widget.invisibleRootItem()

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

        tree_widget.expandAll()
