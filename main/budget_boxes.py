import sys
import os
from datetime import datetime
import json
import itertools
from PyQt6 import QtWidgets as qtw
from PyQt6 import QtGui  as qtg
from PyQt6 import QtCore as qtc


#To have a button allowing to add instances of box from inside the GUI you need a clas that defies "what BOX can look like", but have a json that stores properties for each instance of that class. So class(QLineEdit) can have name, frequency etc.  

class Box_spendings(qtw.QWidget):
    def __init__(self, box_name, frequency, budget_class_parent, tab_root, parent = None): 
        super().__init__(parent)

        self.budget_class_parent = budget_class_parent
        self.tab_root = tab_root

        self.box = qtw.QLineEdit()
        self.validator = qtg.QDoubleValidator(0.00,99999.99,2)
        self.box.setValidator(self.validator)
        self.box.setMaximumWidth(100)
        self.box_descriptor = qtw.QLabel()
        self.box_descriptor.setMaximumWidth(100)
        self.submitted_value = qtw.QLabel()
        self.check_if_registered = qtw.QCheckBox("Registered?")
        self.frequency = frequency
        self.box_name = box_name

        self.setup_submited_value_text()

        self.button_submit = qtw.QPushButton("Submit value")
        self.button_submit.pressed.connect(self.submit_value_input)
        self.button_submit.setMaximumWidth(100)
        self.button_submit.setStyleSheet(self.tab_root.button_formating)
        

        self.box.returnPressed.connect(self.button_submit.click)

        self.box_descriptor.setText(box_name)
        
        layout_horizontal = qtw.QHBoxLayout()

        layout_horizontal.addWidget(self.box_descriptor)
        layout_horizontal.addWidget(self.box)
        layout_horizontal.addWidget(self.button_submit)
        layout_horizontal.addWidget(self.check_if_registered)
        layout_horizontal.addWidget(self.submitted_value)

        self.setLayout(layout_horizontal)

    def setup_submited_value_text(self):
        if self.frequency == 1:
            self.submitted_value.setText(f"monthly")
        else:
            self.submitted_value.setText(f"/ {self.frequency} months")

    def submit_value_input(self):

        value_input = self.box.text()
        value, ok = self.validator.locale().toDouble(value_input) #locale().toDouble() returns a tuple of parsed input and a boolean of whether the parsing was okay, so here we only want the value
        monthly_needs = value / self.frequency

        if self.frequency == 1:
            self.submitted_value.setText((f"{value_input} monthly").replace('.',','))
        else:
            self.submitted_value.setText((f"{value_input} / {self.frequency} months \n {format(monthly_needs, '.2f')} monthly").replace('.',','))
        
        parent = self.budget_class_parent
        
        #if (isinstance(self.budget_class_parent, Budget)): 
        parent.spendings[self.box_name] = monthly_needs 
            
        #if (isinstance(self.budget_class_parent, Budget)):
        if self.check_if_registered.isChecked() == True:
            parent.registered[self.box_name] = monthly_needs

class Box_income(qtw.QWidget):
    def __init__(self, box_name, budget_class_parent, tab_root, parent = None): 
        super().__init__(parent)

        self.budget_class_parent = budget_class_parent
        self.tab_root = tab_root

        self.box = qtw.QLineEdit()
        self.validator = qtg.QDoubleValidator(0.00,99999.99,2)
        self.box.setValidator(self.validator)
        self.box.setMaximumWidth(100)
        self.box_descriptor = qtw.QLabel()
        self.box_descriptor.setMaximumWidth(100)
        self.submitted_value = qtw.QLabel()

        self.box_name = box_name
        self.box_descriptor.setText(self.box_name)

        self.submitted_value.setText(f"monthly")

        self.button_submit = qtw.QPushButton("Submit value")
        self.button_submit.pressed.connect(self.submit_value_input)
        self.button_submit.setMaximumWidth(100)
        self.button_submit.setStyleSheet(self.tab_root.button_formating)

        self.box.returnPressed.connect(self.button_submit.click)
        
        layout_horizontal = qtw.QHBoxLayout()

        layout_horizontal.addWidget(self.box_descriptor)
        layout_horizontal.addWidget(self.box)
        layout_horizontal.addWidget(self.button_submit)
        layout_horizontal.addWidget(self.submitted_value)

        self.setLayout(layout_horizontal)

    def submit_value_input(self):

        value_input = self.box.text()
        value, ok = self.validator.locale().toDouble(value_input) #locale().toDouble() returns a tuple of parsed input and a boolean of whether the parsing was okay, so here we only want the value
        monthly_income = value
        
        self.submitted_value.setText((f"{value_input} monthly").replace('.',','))
        
        parent = self.budget_class_parent
        #if (isinstance(self.budget_class_parent, Budget)): 
        parent.income[self.box_name] = monthly_income
