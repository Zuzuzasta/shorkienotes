import sys
import os
from datetime import datetime
import json
import itertools
from PyQt6 import QtWidgets as qtw
from PyQt6 import QtGui  as qtg
from PyQt6 import QtCore as qtc
from budget_boxes import Box_income, Box_spendings

#Subclassing QWidget ONLY - this will keep one MainWindow instance, and the QTabWidget will let us choose the "main widget"
class Budget(qtw.QWidget):
    def __init__(self, tab_root, parent=None):
        super().__init__(parent)    

        #The budget class will have
            #list of saved past budgetings on the left
            #column composed of the spendings, divided into categories composed of instances of Box class created via json file; in the middle
            #graph plotting the last 6, 12, 24, 36 months for each category and with "effective tax rate"
            #section running calculations and saving new budgetings to json
        
        # Initiating variable containers
        self.spendings = {}
        self.income = {}
        self.registered = {}
        self.list_box_spendings = []
        self.calculated_values = {}

        # This is the Shorkie window
        self.tab_root = tab_root    

        # Current path
        self.current_path = qtc.QDir.currentPath()

        # Setup Month dropdowns
        self.setup_date_dropdowns()

        # Setup button "Add new spending" - add to budget_config.json
        self.setup_button_add_budget_config()

        # Setup button "Clear All" - add to budget_config.json
        self.setup_button_clear_budget_config()
        
        # Setup for main widget / layout elements for the Budget tab
        self.initiate_layouts()

        # Setup for button claculate budgeting
        self.setup_button_calculate()

        # Setup for button submit budgeting to .json
        self.setup_button_submit_budgeting()
        
        # Setup of relevant instances for Box_income and QGroupBox for the income group
        self.setup_income_box_group()  

        # Setup of relevant instances for Box_spendings and QGroupBox for the savings group
        self.setup_savings_box_group()        

        # Setup of relevant instances for QGroupBox for the spendings group
        # Box_spendings instances are later generated from configuration file in "self.read_budget_config_file()"
        self.setup_spendings_box_group()

        # Reads budget_config.json and creates instances of Box_spendings according to the arguments in the file
        self.read_budget_config_file()

        # This connects the buttons submit from all the box_spendings to button calculate
        self.connect_submit_buttons_to_button_calculate()
        
        # Setup for the result display (grid layout)
        self.setup_grid_layout_budget_tab()

        # Setup scrollable part
        self.setup_scrollable_section_inputs_column()

        # Setup extra buttons (add, clear, date combo box)
        self.setup_inputs_column_extra_buttons()

        # Setup Inputs column
        self.setup_inputs_column()

        # QTreeLayout based on budget_history.json
        # 3 headers - month - category - values (for x in dict: key and value)
        self.open_and_load_budget_history()
        self.create_budget_history_tree() 

        # Combines all the sub-widgets into the final layout
        self.setup_main_layout_budget_tab()

    def setup_button_submit_budgeting(self):
        self.button_submit_budgeting = qtw.QPushButton("Submit budgeting to .json")
        self.button_submit_budgeting.setStyleSheet(self.tab_root.button_formating)
        self.button_submit_budgeting.pressed.connect(self.submit_monthly_budgeting_to_json)

    def setup_button_calculate(self):
        self.button_calculate = qtw.QPushButton("Calculate budgeting")
        self.button_calculate.setStyleSheet(self.tab_root.button_formating)
        for instance in self.list_box_spendings:
            self.button_calculate.pressed.connect(instance.submit_value_input)

    def setup_spendings_box_group(self):
        self.spendings_group_border = qtw.QGroupBox("Spendings")
        self.spendings_group_layout_vertical = qtw.QVBoxLayout()

    def initiate_layouts(self):
        self.budget_tab_layout_horizontal = qtw.QHBoxLayout()
        self.inputs_column_layout = qtw.QVBoxLayout()        
        self.inputs_column_buttons_and_results = qtw.QVBoxLayout()
        self.inputs_column_layout_vertical_scroll = qtw.QVBoxLayout()

    def setup_button_clear_budget_config(self):
        self.button_clear_budget_config = qtw.QPushButton("Clear All")
        self.button_clear_budget_config.setIcon(qtg.QIcon.fromTheme("list-remove"))
        self.button_clear_budget_config.setMaximumWidth(200)
        self.button_clear_budget_config.setStyleSheet(self.tab_root.button_formating)

        self.button_clear_budget_config.pressed.connect(self.clear_all_budget_inputs)

    def setup_button_add_budget_config(self):
        self.button_add_budget_config = qtw.QPushButton("Add new spending category")
        self.button_add_budget_config.setIcon(qtg.QIcon.fromTheme("list-add"))
        self.button_add_budget_config.setMaximumWidth(200)
        self.button_add_budget_config.setStyleSheet(self.tab_root.button_formating)

        self.button_add_budget_config.pressed.connect(self.open_budget_config_window)

    def setup_date_dropdowns(self):
        self.month_dropdown = qtw.QComboBox()
        self.month_dropdown.addItems([
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December"
                ]
            )
        
        self.year_dropdown = qtw.QComboBox()
        self.year_dropdown.addItems(["2026","2027"])

    def clear_all_budget_inputs(self):

        self.box_basic_income.box.setText("")
        self.box_basic_income.submitted_value.setText(f"monthly")
        
        self.box_extra_income.box.setText("")
        self.box_extra_income.submitted_value.setText(f"monthly")

        self.box_savings.box.setText("")
        self.box_savings.submitted_value.setText(f"monthly")

        for instance in self.list_box_spendings:
            instance.box.setText("")
            instance.submitted_value.setText("")
            instance.setup_submited_value_text()

        self.income_label_bot.setText(f"0 DKK")
        self.spendings_label_bot.setText(f"0 DKK")
        self.registered_label_bot.setText(f"0 DKK")
        self.savings_label_bot.setText(f"0 DKK")
        self.remaining_label_bot.setText(f"0 DKK")

    def create_budget_history_tree(self):
        self.budget_history_tree = qtw.QTreeWidget()
        self.budget_history_tree.setMinimumWidth(500)
        self.budget_history_tree.setColumnCount(4)
        self.budget_history_tree.setHeaderLabels([
                "Month", 
                "Category", 
                "Value category",
                "Entry Name", 
                "Amount"
                ]
            )

        self.budget_history_tree.itemClicked.connect(self.collapse_when_clicked)
        self.budget_history_tree.itemDoubleClicked.connect(self.load_when_double_clicked)

        for entry in self.history_data:
            for month, history_category in entry.items():
                month_item = qtw.QTreeWidgetItem()
                month_item.setText(0,month)
                self.budget_history_tree.addTopLevelItem(month_item)

                inputs_item = qtw.QTreeWidgetItem()
                inputs_item.setText(1,"Inputs") 
                month_item.addChild(inputs_item)

                for value_category, value_name in history_category["Inputs"].items():
                    value_item = qtw.QTreeWidgetItem()
                    value_item.setText(2,value_category)
                    inputs_item.addChild(value_item)  

                    for name, value  in value_name.items():
                        amount_item = qtw.QTreeWidgetItem()
                        amount_item.setText(3,name)
                        amount_item.setText(4,f"{value}")
                        value_item.addChild(amount_item)

                results_item = qtw.QTreeWidgetItem()
                results_item.setText(1,"Results") 
                month_item.addChild(results_item)

                for value_category, value in history_category["Results"].items():
                    result_item = qtw.QTreeWidgetItem()
                    result_item.setText(2,value_category)
                    result_item.setText(4,f"{value}")
                    results_item.addChild(result_item)

    def collapse_when_clicked(self,item,column):
        # toggle expansion on click
        expanded = item.isExpanded()
        item.setExpanded(not expanded)

    def load_when_double_clicked(self,item,column):

        self.item = item
        self.column = column

        if column == 1:
            # load just inputs to all inputs fields
            for category in range(0,item.childCount()):
                for row in range(0,item.child(category).childCount()):
                    self.load_specified_value(self.item.child(category).child(row))                

        elif column == 2:
            # load specified section into it's boxes
            for row in range(0,self.item.childCount()):
                self.load_specified_value(self.item.child(row))
                                       
        elif column == 3 or column == 4:
            # load specified value into it's box
            self.load_specified_value(self.item)

    def load_specified_value(self,item):
        if item.text(3) == self.box_basic_income.box_descriptor.text():
            self.box_basic_income.box.setText(item.text(4).replace('.',','))
        elif item.text(3) == self.box_extra_income.box_descriptor.text():
            self.box_extra_income.box.setText(item.text(4).replace('.',','))
        elif item.text(3) == self.box_savings.box_descriptor.text():
            self.box_savings.box.setText(item.text(4).replace('.',','))
        else:
            for instance in self.list_box_spendings:
                if instance.box_descriptor.text() == item.text(3):
                    value_to_load = float(item.text(4)) * instance.frequency
                    instance.box.setText(str(value_to_load).replace('.',','))

    def open_budget_config_window(self):
        # TODO refactor this function
        budget_config_window = qtw.QDialog()
        budget_config_window.setWindowTitle("Add new spending")

        self.new_spending_name_input = qtw.QLineEdit()

        self.dropdown_frequency = qtw.QComboBox()
        self.dropdown_frequency.addItems(["1","2","3"])

        button_add_new_configuration = qtw.QPushButton("Add new spending")
        button_add_new_configuration.setMaximumWidth(150)
        button_add_new_configuration.pressed.connect(self.update_budget_config_json)

        layout_budget_config_window = qtw.QHBoxLayout()
        layout_budget_config_window.addWidget(self.new_spending_name_input)
        layout_budget_config_window.addWidget(self.dropdown_frequency)
        layout_budget_config_window.addWidget(button_add_new_configuration)

        budget_config_window.setLayout(layout_budget_config_window)  

        budget_config_window.exec()

    def update_budget_config_json(self):
        main_path = qtc.QDir.currentPath()

        with open(os.path.join(main_path,"main","config", "budget_config.json"), "r") as budget_config_file:
            budget_config = json.load(budget_config_file)

        self.chosen_frequency = self.dropdown_frequency.currentText()
        self.chosen_frequency_value, ok = self.locale().toDouble(self.chosen_frequency)

        with open(os.path.join(main_path,"main","config", "budget_config.json"), "w") as budget_config_file:  
            budget_config.append([self.new_spending_name_input.text(),int(self.chosen_frequency_value)])
            json.dump(budget_config,budget_config_file)

        self.read_budget_config_file()

    def connect_submit_buttons_to_button_calculate(self):
        self.button_calculate.pressed.connect(self.box_basic_income.submit_value_input)
        self.button_calculate.pressed.connect(self.box_extra_income.submit_value_input)
        self.button_calculate.pressed.connect(self.box_savings.submit_value_input)
        self.button_calculate.pressed.connect(self.calculate_budgeting)

    def setup_income_box_group(self):
        self.box_basic_income = Box_income("Salary / Income", self, self.tab_root,self)
        self.box_extra_income = Box_income("Extra Income", self, self.tab_root,self)

        self.income_group_border = qtw.QGroupBox("Income")
        self.income_group_layout_vertical = qtw.QVBoxLayout()

        self.income_group_layout_vertical.addWidget(self.box_basic_income)
        self.income_group_layout_vertical.addWidget(self.box_extra_income)     
        self.income_group_border.setLayout(self.income_group_layout_vertical)

    def setup_savings_box_group(self):
        self.box_savings = Box_spendings("Savings", 1, self, self.tab_root, self) 
        self.box_savings.box.setText("5000")
        self.box_savings.check_if_registered.hide()

        self.savings_group_border = qtw.QGroupBox("Savings")
        self.savings_group_layout_vertical = qtw.QVBoxLayout()

        self.savings_group_layout_vertical.addWidget(self.box_savings)
        self.savings_group_border.setLayout(self.savings_group_layout_vertical)

    def setup_main_layout_budget_tab(self):

        # Three columns are merged here!
        self.budget_tab_layout_horizontal.addWidget(self.budget_history_tree)
        self.budget_tab_layout_horizontal.addLayout(self.inputs_column_layout)
        # todo self.budget_tab_layout_horizontal.addLayout(graph)

        self.setLayout(self.budget_tab_layout_horizontal)

    def setup_inputs_column(self):
        self.inputs_column_buttons_and_results.addWidget(self.button_calculate)
        self.inputs_column_buttons_and_results.addLayout(self.grid_layout_for_results)
        self.inputs_column_buttons_and_results.addWidget(self.button_submit_budgeting)

        self.inputs_column_layout.addWidget(self.scroll_budget)
        self.inputs_column_layout.addLayout(self.extra_buttons)
        self.inputs_column_layout.addLayout(self.inputs_column_buttons_and_results)

    def setup_inputs_column_extra_buttons(self):
        self.extra_buttons = qtw.QHBoxLayout()
        self.extra_buttons.addWidget(self.button_add_budget_config)
        self.extra_buttons.addWidget(self.button_clear_budget_config)
        self.extra_buttons.addWidget(self.month_dropdown)
        self.extra_buttons.addWidget(self.year_dropdown)

    def setup_scrollable_section_inputs_column(self):
        self.inputs_column_layout_vertical_scroll.addWidget(self.income_group_border)
        self.inputs_column_layout_vertical_scroll.addWidget(self.savings_group_border)
        self.inputs_column_layout_vertical_scroll.addWidget(self.spendings_group_border)
        
        scroll_container = qtw.QWidget()
        scroll_container.setLayout(self.inputs_column_layout_vertical_scroll)

        self.scroll_budget = qtw.QScrollArea()
        self.scroll_budget.setVerticalScrollBarPolicy(qtc.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll_budget.setHorizontalScrollBarPolicy(qtc.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_budget.setWidgetResizable(True)
        self.scroll_budget.setWidget(scroll_container)

    def setup_grid_layout_budget_tab(self):
        self.grid_layout_for_results = qtw.QGridLayout()

        income_label_top = qtw.QLabel()
        spendings_label_top = qtw.QLabel()
        registered_label_top = qtw.QLabel()
        savings_label_top = qtw.QLabel()
        remaining_label_top = qtw.QLabel()

        self.income_label_bot = qtw.QLabel()
        self.spendings_label_bot = qtw.QLabel()
        self.registered_label_bot = qtw.QLabel()
        self.savings_label_bot = qtw.QLabel()
        self.remaining_label_bot = qtw.QLabel()
        
        income_label_top.setText("Your total income:")
        income_label_top.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        spendings_label_top.setText("Your total spendings: \n (including savings)")
        spendings_label_top.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        registered_label_top.setText("Amount registered for \n Betalingskort \\ Automatic \n payments")
        registered_label_top.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        savings_label_top.setText("Amount put in savings:")
        savings_label_top.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        remaining_label_top.setText("Remaining amount:")
        remaining_label_top.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

        self.income_label_bot.setText(f"0 DKK")
        self.income_label_bot.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        self.spendings_label_bot.setText(f"0 DKK")
        self.spendings_label_bot.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        self.registered_label_bot.setText(f"0 DKK")
        self.registered_label_bot.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        self.savings_label_bot.setText(f"0 DKK")
        self.savings_label_bot.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)
        self.remaining_label_bot.setText(f"0 DKK")
        self.remaining_label_bot.setAlignment(qtc.Qt.AlignmentFlag.AlignCenter)

        self.grid_layout_for_results.addWidget(income_label_top,0,0)
        self.grid_layout_for_results.addWidget(spendings_label_top,0,1)
        self.grid_layout_for_results.addWidget(registered_label_top,0,2)
        self.grid_layout_for_results.addWidget(savings_label_top,0,3)
        self.grid_layout_for_results.addWidget(remaining_label_top,0,4)

        self.grid_layout_for_results.addWidget(self.income_label_bot,1,0)
        self.grid_layout_for_results.addWidget(self.spendings_label_bot,1,1)
        self.grid_layout_for_results.addWidget(self.registered_label_bot,1,2)
        self.grid_layout_for_results.addWidget(self.savings_label_bot,1,3)
        self.grid_layout_for_results.addWidget(self.remaining_label_bot,1,4)

    def read_budget_config_file(self):

        main_path = qtc.QDir.currentPath()

        with open(os.path.join(main_path, "main", "config" , "budget_config.json"), "r") as budget_config_file:
            budget_config = json.load(budget_config_file) 

        for box in self.list_box_spendings:
            self.spendings_group_layout_vertical.removeWidget(box)
            box.setParent(None)
        self.list_box_spendings.clear()      # clear Python list

        #Create instance of Box class with input from list in json file passed as arguments
        for parameter_list in budget_config:
            box_config = parameter_list

            self.box_spendings = Box_spendings(box_config[0],box_config[1],self,self.tab_root, self)

            self.list_box_spendings.append(self.box_spendings)

            self.spendings_group_layout_vertical.addWidget(self.box_spendings)

        self.spendings_group_border.setLayout(self.spendings_group_layout_vertical)

    def calculate_budgeting(self):
        total_income = float()
        total_costs = float()
        total_registered_costs = float()

        for cost in self.spendings:
            total_costs += float(self.spendings[cost])

        for profit in self.income:
            total_income += float(self.income[profit])

        for cost in self.registered:
            total_registered_costs += float(self.registered[cost])

        left_in_budget = total_income - total_costs

        #Truncated values
        total_income_2f = round(total_income,2)
        total_costs_2f = round(total_costs,2)
        total_registered_costs_2f = round(total_registered_costs,2)
        savings_2f = round(self.spendings['Savings'],2)
        left_in_budget_2f = round(left_in_budget,2)

        #Update widget display          
        self.income_label_bot.setText(f"{total_income_2f} DKK")
        self.spendings_label_bot.setText(f"{total_costs_2f} DKK")
        self.registered_label_bot.setText(f"{total_registered_costs_2f} DKK")
        self.savings_label_bot.setText(f"{savings_2f} DKK")
        self.remaining_label_bot.setText(f"{left_in_budget_2f} DKK")

        self.calculated_values["Income"] = total_income_2f
        self.calculated_values["Spendings"] = total_costs_2f
        self.calculated_values["Registered to Betalingskort"] = total_registered_costs_2f
        self.calculated_values["Savings"] = savings_2f
        self.calculated_values["Remaining"] = left_in_budget_2f


    def submit_monthly_budgeting_to_json(self):
        
        budget_month = self.month_dropdown.currentText() + "_" + self.year_dropdown.currentText()
        monthly_budgeting = {
            budget_month : {
                "Results": self.calculated_values,
                "Inputs" : {
                    "Income" : self.income,
                    "Spendings" : self.spendings
                }
            }
        }
    
        self.open_and_load_budget_history()

        self.history_data.append(monthly_budgeting)

        with open(os.path.join(self.current_path,"main","config" ,"budget_history.json"), "w") as self.history_file:
            json.dump(self.history_data, self.history_file)
        
        self.refresh_tree_in_budget_tab()

    def refresh_tree_in_budget_tab(self):
        self.budget_tab_layout_horizontal.removeWidget(self.budget_history_tree)
        self.open_and_load_budget_history()
        self.create_budget_history_tree()
        self.budget_tab_layout_horizontal.insertWidget(0, self.budget_history_tree)

    def open_and_load_budget_history(self):
        with open(os.path.join(self.current_path, "main", "config" , "budget_history.json"), "r") as self.history_file:
            self.history_data = json.load(self.history_file)

