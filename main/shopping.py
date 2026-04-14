import sys
import os
from datetime import datetime
import json
import itertools
from PyQt6 import QtWidgets as qtw
from PyQt6 import QtGui  as qtg
from PyQt6 import QtCore as qtc

#Subclassing QWidget ONLY - this will keep one MainWindow instance, and the QTabWidget will let us choose the "main widget"
class Shopping(qtw.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)    

        # Current path
        self.current_path = qtc.QDir.currentPath()

        # "Add produce" line edit + button
        self.add_produce_to_database_dialog()

        # "Add to list"
        self.add_produce_to_shopping_list_dialog()

        # Make tree view
        self.construct_shopping_list_tree_display()

        #* Construct page
        self.shopping_tab_layout()

    
    def add_produce_to_database_dialog(self):
        self.open_and_load_product_database()
        
        self.produce_dialog_layout = qtw.QHBoxLayout()
        self.produce_name_type_in = qtw.QLineEdit()
        self.produce_category_combo = qtw.QComboBox()

        self.produce_category_combo.addItems([produce_category for produce_category in self.product_database.keys()])
        
        produce_add_button = qtw.QPushButton("Add produce to the database")
        produce_add_button.clicked.connect(self.add_produce_to_database_button)

        self.produce_name_type_in.returnPressed.connect(produce_add_button.click)

        self.produce_dialog_layout.addWidget(self.produce_name_type_in)
        self.produce_dialog_layout.addWidget(self.produce_category_combo)
        self.produce_dialog_layout.addWidget(produce_add_button)

    def add_produce_to_database_button(self):

        self.open_and_load_product_database()

        for produce_category, produce in self.product_database.items():
            if produce_category == self.produce_category_combo.currentText():
                produce.append(self.produce_name_type_in.text())
                self.save_produce_to_file(produce_category, produce)

        self.apply_completer_to_line_edit()

    def save_produce_to_file(self, produce_category, produce):

        self.product_database[produce_category] = produce

        with open(os.path.join(self.current_path, "main", "config" , "product_database.json"), "w") as product_database_file:
            json.dump(self.product_database,product_database_file)
    
    def open_and_load_product_database(self):

        with open(os.path.join(self.current_path, "main", "config" , "product_database.json"), "r") as product_database_file:
            self.product_database: dict = json.load(product_database_file)

    def add_produce_to_shopping_list_dialog(self):
        self.open_and_load_product_database()
        
        self.add_produce_layout = qtw.QHBoxLayout()

        self.add_produce_type_in = qtw.QLineEdit()

        self.choose_produce_category_combo = qtw.QComboBox()
        self.choose_produce_category_combo.addItems([produce_category for produce_category in self.product_database.keys()])

        #? BTW QComboBox has a lineEdit option - maybe there is a need to rewrite the code a bit...
        self.choose_produce_combo = qtw.QComboBox()
        self.setup_for_choose_produce_combo()
        
        self.choose_produce_category_combo.currentIndexChanged.connect(self.choose_produce_combo_refresh)

        self.add_produce_to_list_button = qtw.QPushButton("Add to shopping list")
        self.add_produce_to_list_button.pressed.connect(self.appending_produce_to_shopping_list_button)
        
        #? not sure if pressing enter here will also submit the popup selection or does it override that... (.activated / .popup)
        self.add_produce_type_in.returnPressed.connect(self.add_produce_to_list_button.click)

        self.apply_completer_to_line_edit()

        self.add_produce_layout.addWidget(self.choose_produce_category_combo)
        self.add_produce_layout.addWidget(self.choose_produce_combo)
        self.add_produce_layout.addWidget(self.add_produce_type_in)
        self.add_produce_layout.addWidget(self.add_produce_to_list_button)

    def apply_completer_to_line_edit(self):
        produce_list = self.generate_lit_of_produce()

        produce_completer = qtw.QCompleter(produce_list)
        produce_completer.setCaseSensitivity(qtc.Qt.CaseSensitivity.CaseInsensitive)
        self.add_produce_type_in.setCompleter(produce_completer)

    def setup_for_choose_produce_combo(self):
        for produce_category, produce_list in self.product_database.items():
            if self.choose_produce_category_combo.currentText() == produce_category:
                self.choose_produce_combo.addItems(produce_list)

    def choose_produce_combo_refresh(self):
        self.choose_produce_combo.clear()
        self.add_produce_layout.removeWidget(self.choose_produce_combo)
        self.setup_for_choose_produce_combo()
        self.add_produce_layout.insertWidget(1,self.choose_produce_combo)

    def generate_lit_of_produce(self) -> list:
        self.open_and_load_product_database()
        produce_list: list = []

        for produce_category, produce in self.product_database.items():
            produce_list = [*produce_list, *produce]
        return produce_list

    def appending_produce_to_shopping_list_button(self):

        self.open_and_load_product_database()
        self.open_and_load_shopping_list()

        for produce_category_in_database, produce_list_in_database in self.product_database.items():

            if self.add_produce_type_in.text() in produce_list_in_database:

                if produce_category_in_database not in self.shopping_list.keys():
                    self.shopping_produce_list = []
                else:
                    self.shopping_produce_list = self.shopping_list[produce_category_in_database]

                self.shopping_produce_list.append(self.add_produce_type_in.text())
                self.shopping_list[produce_category_in_database] = self.shopping_produce_list
                self.save_produce_to_shopping_list(self.shopping_list)
        
        self.refresh_shopping_list_tree_view()

    def open_and_load_shopping_list(self):
        with open(os.path.join(self.current_path, "main", "config" , "shopping_list.json"), "r") as shopping_list_file:
            self.shopping_list: dict = json.load(shopping_list_file)


    def save_produce_to_shopping_list(self, dictionary_entry):
        with open(os.path.join(self.current_path, "main", "config" , "shopping_list.json"), "w") as shopping_list_file:
            json.dump(dictionary_entry,shopping_list_file)
 

    # TODO: html file generator for sending as link / attachment with check boxes

    def construct_shopping_list_tree_display(self):
        self.shopping_tree = qtw.QTreeWidget()
        self.shopping_tree.setColumnCount(2)
        self.shopping_tree.setHeaderLabels(["Category","Produce"])

        self.open_and_load_shopping_list()

        for produce_category, produce_list in self.shopping_list.items():
            category_item = qtw.QTreeWidgetItem()
            category_item.setText(0,produce_category)
            self.shopping_tree.addTopLevelItem(category_item)

            for produce in produce_list:
                produce_item = qtw.QTreeWidgetItem()
                produce_item.setText(1,produce)
                category_item.addChild(produce_item)

        self.shopping_tree.expandAll()

    def refresh_shopping_list_tree_view(self):
        self.shopping_list_layout.removeWidget(self.shopping_tree)
        self.open_and_load_shopping_list()
        self.construct_shopping_list_tree_display()
        self.shopping_list_layout.insertWidget(1,self.shopping_tree)

    def generate_list_html(self):
        pass

    def shopping_tab_layout(self):
        self.shopping_inputs_layout = qtw.QVBoxLayout()
        self.shopping_inputs_layout.addLayout(self.produce_dialog_layout)
        self.shopping_inputs_layout.addLayout(self.add_produce_layout)

        self.shopping_list_layout = qtw.QVBoxLayout()
        self.shopping_list_layout.addWidget(self.shopping_tree)

        self.shopping_main_layout = qtw.QHBoxLayout()
        self.shopping_main_layout.addLayout(self.shopping_inputs_layout)
        self.shopping_main_layout.addLayout(self.shopping_list_layout)

        self.setLayout(self.shopping_main_layout)