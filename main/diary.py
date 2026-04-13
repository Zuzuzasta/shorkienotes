import os
from datetime import datetime
import json
import itertools
from PyQt6 import QtWidgets as qtw
from PyQt6 import QtGui  as qtg
from PyQt6 import QtCore as qtc


#Subclassing QWidget ONLY - this will keep one MainWindow instance, and the QTabWidget will let us choose the "main widget"
class Diary(qtw.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)    

        #Create a multi line text input field with QTextEdit
        self.text_editor = qtw.QTextEdit()
        self.text_editor.setPlaceholderText("Write your diary entry <3")

        # store the last selected index, we need this to grey out the edit
        self.index_of_selected_entry = None

        self.button_edit = qtw.QPushButton("Edit diary entry") #Define button widget

        self.button_edit.setEnabled(False)
        self.button_edit.pressed.connect(self.edit_note)

        self.button_edit.setStyleSheet(parent.button_formating)

        self.button_add = qtw.QPushButton("Add new diary entry") #Define button widget
        self.button_add.pressed.connect(self.save_note)

        self.button_add.setStyleSheet(parent.button_formating)

        self.button_new = qtw.QPushButton("Open new diary entry")
        self.button_new.pressed.connect(self.open_new)

        self.button_new.setStyleSheet(parent.button_formating)

        #Layout - buttons

        layout_buttons = qtw.QHBoxLayout()

        layout_buttons.addWidget(self.button_edit)
        layout_buttons.addWidget(self.button_add)

        #Layout - vertical text over buttons

        layout_vertical = qtw.QVBoxLayout()

        layout_vertical.addWidget(self.button_new)
        layout_vertical.addWidget(self.text_editor)
        layout_vertical.addLayout(layout_buttons)

        # Making a model for the file with entries and creating a vidget for it:

        self.current_path = qtc.QDir.currentPath()
        self.entries_folder = qtg.QFileSystemModel()
        self.entries_path = qtc.QDir(self.current_path).filePath("entries")
        self.entries_folder.setRootPath(self.entries_path)
        
        self.entries_list = qtw.QListView()
        self.entries_list.setModel(self.entries_folder)
        self.entries_list.setRootIndex(self.entries_folder.index(self.entries_path))

        self.entries_list.clicked.connect(self.entry_selected)

        #Layout - horizontal - left list - right input

        layout_horizontal = qtw.QHBoxLayout()
        
        layout_horizontal.addWidget(self.entries_list)
        layout_horizontal.addLayout(layout_vertical)

        #widget = qtw.QWidget()
        self.setLayout(layout_horizontal)

    def save_note(self):
        # Get the text from QTextEdit
        new_note = self.text_editor.toPlainText()
    
        self.current_path = qtc.QDir.currentPath()
        self.entries_path = qtc.QDir(self.current_path).filePath("entries")

        # make today object with today.day today.month and today.year attributes
        today = datetime.now()

        # This is our json file name, it is made of string of todays date and _note_entry - however, without the .json extension as it would be annoying to concatenate later
        json_file_name = f"{today.day:02d}_{today.month:02d}_{today.year:02d}"
        json_file_name_full = str()
        path_check = os.path.isfile(os.path.join(self.entries_path, json_file_name + f".json"))

        # Now, check if file exists, if yes, iterate through itertools.count(1) (from 1 to infity), find the first one where number was not used and add "_number" and .json extension
        if path_check == True:
            for file_number in itertools.count(1):
                if os.path.isfile(os.path.join(self.entries_path, json_file_name + f"_" + f"{file_number}" + f".json")) == True:
                    continue
                else:
                    json_file_name_full = json_file_name + f"_" + f"{file_number}" + f".json"  
                    break                                   
        else:
            json_file_name_full = json_file_name + f".json"

        json_file = open(os.path.join(self.entries_path, json_file_name_full), "w")
        json.dump(new_note, json_file)
        json_file.close()

    def open_new(self):
        self.index_of_selected_entry = None
        self.button_edit.setEnabled(False)
        self.text_editor.setText(None)

    def edit_note(self):
        if self.index_of_selected_entry is None:
            return
        # Get the text from QTextEdit
        edited_note = self.text_editor.toPlainText()
        open_json = open(self.entries_folder.filePath(self.index_of_selected_entry), "w")
        json.dump(edited_note, open_json)
        open_json.close()

    def entry_selected(self,index):
        self.index_of_selected_entry = index
        self.button_edit.setEnabled(True)
        open_json = open(self.entries_folder.filePath(index))
        text_from_json = json.load(open_json)
        self.text_editor.setText(text_from_json)
        open_json.close()
