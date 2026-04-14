import sys
import os
from datetime import datetime
import json
import itertools
from PyQt6 import QtWidgets as qtw
from PyQt6 import QtGui  as qtg
from PyQt6 import QtCore as qtc
from diary import Diary
from budget import Budget
from shopping import Shopping

# Subclass QMainWindow to have it "self contained" and allow us to customize the main window
class Shorkie(qtw.QMainWindow):
    def __init__(self):
        super().__init__() 
        self.setWindowTitle("Shorkie Notes")
        self.setWindowIcon(qtg.QIcon(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"icon" ,"ShorkieNotesIcon.ico")))

        self.header_tabs = qtw.QTabWidget()

        self.header_tabs.setStyleSheet("""
            QTabBar::tab {
                border-radius: 3px;
                padding: 6px 12px;
            }
                                       
            QTabBar::tab:selected {
                background: #3366cc;   /* blue */
                color: #c2d1f0;
                font-weight: bold;

            }
            QTabBar::tab:!selected {
                background: #c2d1f0; /* light blue */
                color: #193167;
            }
        """)

        self.button_formating = """
            QWidget {
                background: #c2d1f0;   /* light blue */
                border-radius: 3px;
                padding: 6px 12px;
                color: #193167;
            }
        """

        self.diary_class = Diary(self)
        self.header_tabs.addTab(self.diary_class, "Diary")

        self.budget_class = Budget(tab_root=self,parent=self)
        self.header_tabs.addTab(self.budget_class, "Budget")

        self.shopping_class = Shopping(self)
        self.header_tabs.addTab(self.shopping_class, "Shopping Lists")

        self.setCentralWidget(self.header_tabs) 
        self.setGeometry(600, 100, 1000, 900) 

# The main application object QApplication. (sys.argv) allows to pass arguments form the console
if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)

    window = Shorkie()
    window.show()

    sys.exit(app.exec())