import os
import sys

from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTextEdit, QLineEdit, \
    QPushButton, QFileDialog, QDialog


class SaveTagsDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Save Tags")
        self.layout = QVBoxLayout()

        # First part: Tags group
        self.tags_group = QGroupBox("Tags")
        self.tags_layout = QVBoxLayout()
        self.text_tags = QTextEdit()
        self.tags_layout.addWidget(self.text_tags)
        self.tags_group.setLayout(self.tags_layout)
        self.layout.addWidget(self.tags_group, 1)

        # Second part: 附加信息 group
        self.extras_group = QGroupBox("附加信息")
        self.extras_layout = QVBoxLayout()
        self.text_extras = QTextEdit()
        self.extras_layout.addWidget(self.text_extras)
        self.extras_group.setLayout(self.extras_layout)
        self.layout.addWidget(self.extras_group, 1)

        # # Third part: 保存路径 group
        # self.save_path_group = QGroupBox("保存路径")
        # self.save_path_layout = QHBoxLayout()
        # self.save_path = QLineEdit()
        # self.browse_button = QPushButton("Browse")
        # self.browse_button.clicked.connect(self.browse_file)
        # self.save_path_layout.addWidget(self.save_path)
        # self.save_path_layout.addWidget(self.browse_button)
        # self.save_path_group.setLayout(self.save_path_layout)
        # self.layout.addWidget(self.save_path_group)

        # Fourth part: 保存 and 取消 buttons
        self.buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")
        self.save_button.clicked.connect(self.save_file)
        self.cancel_button.clicked.connect(self.close)
        self.buttons_layout.addWidget(self.save_button)
        self.buttons_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.buttons_layout)

        if self.text_extras.toPlainText():
            self.text_extras.append("\n\n")
        self.text_extras.append("Comments: ")
        self.text_extras.moveCursor(QTextCursor.End)
        
        self.setLayout(self.layout)
        self.resize(800, 600)

    # def browse_file(self):
    #     options = QFileDialog.Options()
    #     file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "SDTags (*.sdtags)", options=options)
    #     if file_name:
    #         self.save_path.setText(file_name)

    def save_file(self):
        depot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'depot')
        if not os.path.exists(depot_path):
            os.makedirs(depot_path)

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        extension = '.sdtags'
        file_name, _ = QFileDialog.getSaveFileName(self, "Save File", depot_path, "SDTags (*%s)" % extension, options=options)
        if file_name:
            with open(file_name, 'w') as file:
                file.write(self.text_tags.toPlainText())
                file.write('\n\n')
                file.write(self.text_extras.toPlainText())
            self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SaveTagsDialog()
    window.show()
    sys.exit(app.exec_())





