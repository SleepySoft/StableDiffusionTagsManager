import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget

from TagManager import TagManager
from AnalyserWindow import AnalyserWindow
from GenerateWindow import GenerateWindow
from defines import PUBLIC_DATABASE, PRIVATE_DATABASE, BACKUP_LIMIT


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.tag_manager = TagManager(PUBLIC_DATABASE, PRIVATE_DATABASE, BACKUP_LIMIT)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.analysis_tab = AnalyserWindow(self.tag_manager)
        self.generate_tab = GenerateWindow(self.tag_manager)

        self.init_ui()

    def init_ui(self):
        self.tabs.addTab(self.analysis_tab, "Analysis")
        self.tabs.addTab(self.generate_tab, "Generate")
        self.setCentralWidget(self.tabs)
        self.resize(1280, 800)
        self.setWindowTitle('Stable Diffusion Tag 分析管理 - Sleepy')

    def on_tab_changed(self, index):
        if index == 0:
            self.analysis_tab.on_widget_activated()
        else:
            self.generate_tab.on_widget_activated()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
