import sys
import os
from datetime import datetime
import json
import itertools
from PyQt6 import QtWidgets as qtw
from PyQt6 import QtGui  as qtg
from PyQt6 import QtCore as qtc
import pandas as pd
import pyqtgraph as pg

class Plot_area(qtw.QWidget):
    def __init__(self, budget_class_parent, tab_root, parent = None): 
        super().__init__(parent)

        self.budget_class_parent = budget_class_parent
        self.tab_root = tab_root

        #Use self.open_and_load_budget_history() that is located inside Budget class => here parent is the Budget class
        parent.open_and_load_budget_history()

        # Get keys from budget_history.json stored in history_data list of dictionaries
        month_year = []

        for budget_data in parent.history_data:
            for month_year_data in budget_data:
                month_year.append(month_year_data)

        #Create X-axis based on data
        x_axis_month = []

        for month_year_entry in month_year:
            #Generate string that is only Month name (replace "_2026" with " ")
            x_axis_month.append(month_year_entry.replace(month_year_entry[-5:],""))
            #TODO x_axis_year = month_year_entry[-5:]

        x_axis_month_dictionary = dict(enumerate(x_axis_month))

        #Y-axes

        income_total = []
        income_extra = []
        registered = []
        spendings_total = []
        savings = []
        remaining = []
        rent = []
        #TODO effective_tax_rate = []
        cost_of_living = [] #income_total-(spendings_total-savings)
        cost_of_living_index = [] #income_total/cost_of_living


        for budget_data in parent.history_data:
            for month_year_data, value in budget_data.items():
                income_total.append(value["Results"]["Income"])
                income_extra.append(value["Inputs"]["Income"]["Extra Income"])
                registered.append(value["Results"]["Registered to Betalingskort"])
                spendings_total.append(value["Results"]["Spendings"])
                savings.append(value["Results"]["Savings"])
                remaining.append(value["Results"]["Remaining"])
                rent.append(value["Inputs"]["Spendings"]["Rent"])
                #TODO effective_tax_rate
                #Cost of living calculations
                total_cost = value["Results"]["Spendings"] - value["Results"]["Savings"]
                cost_of_living.append(total_cost)
                total_cost_index = value["Results"]["Income"] / total_cost
                cost_of_living_index.append(total_cost_index)

        #String axis
        month_axis = pg.AxisItem(orientation="bottom")
        month_axis.setTicks([list(x_axis_month_dictionary.items())])

        self.plot_graph = pg.PlotWidget(axisItems={"bottom": month_axis})
        background_color = None
        self.plot_graph.setBackground(background_color)
        self.plot_graph.setTitle("Budget summary", color="w", size="18pt")

        #Setting up axis labels, using html <span> and CSS styles
        self.plot_graph.setLabel("left", "<span style='color: white; font-size:12pt'>Amount (DKK)</span>")
        self.plot_graph.setLabel("bottom", "<span style='color: white; font-size:12pt'>Month</span>")

        #self.plot_graph.addLegend()
        legend_widget = pg.GraphicsLayoutWidget()
        legend_widget.setBackground(background_color)
        legend = pg.LegendItem(colCount=1, offset=(0,0), labelTextSize="10pt")
        legend_widget.addItem(legend)
        legend_widget.setMaximumWidth(200)


        self.plot_graph.showGrid(x=True, y=True)

        #TODO .setYrange can be modifible from UI

        # Pen colors
        pen_income_extra = pg.mkPen(color=(255, 51, 51), width=5)
        pen_income_total = pg.mkPen(color=(128, 0, 0), width=5)
        pen_registered = pg.mkPen(color=(102, 255, 102), width=5)
        pen_spendings_total = pg.mkPen(color=(0, 128, 0), width=5)
        pen_savings = pg.mkPen(color=(0, 191, 255), width=5)
        pen_remaining = pg.mkPen(color=(255, 204, 0), width=5)
        pen_rent = pg.mkPen(color=(217, 102, 255), width=5)
        #TODO pen_effective_tax_rate = pg.mkPen(color=(255, 0, 0), width=5)
        pen_cost_of_living = pg.mkPen(color=(255, 255, 255), width=5) 
        pen_cost_of_living_index = pg.mkPen(color=(255, 0, 0), width=5) 


        self.plot_line("Total Income", list(x_axis_month_dictionary.keys()), income_total, pen_income_total)
        self.plot_line("Extra Income", list(x_axis_month_dictionary.keys()), income_extra, pen_income_extra)
        self.plot_line("Registered spendings", list(x_axis_month_dictionary.keys()), registered, pen_registered)
        self.plot_line("Total spendings", list(x_axis_month_dictionary.keys()), spendings_total, pen_spendings_total)
        self.plot_line("Savings", list(x_axis_month_dictionary.keys()), savings, pen_savings)
        self.plot_line("Remaining (Fun)", list(x_axis_month_dictionary.keys()), remaining, pen_remaining)
        self.plot_line("Rent", list(x_axis_month_dictionary.keys()), rent, pen_rent)
        self.plot_line("Cost of living", list(x_axis_month_dictionary.keys()), cost_of_living, pen_cost_of_living)

        #populate legend dynamically
        for item in self.plot_graph.listDataItems():
            # item.name() automatically retrieves the "name" string you set inside .plot()
            legend.addItem(item, name=item.name())

        #Setup layout of the Plot_area widget, and place the graph there
        plot_layout = qtw.QHBoxLayout()
        plot_layout.addWidget(legend_widget)
        plot_layout.addWidget(self.plot_graph)
        self.setLayout(plot_layout)

    def plot_line(self, name, month, amount, pen):
        self.plot_graph.plot(
            month,
            amount,
            name=name,
            pen=pen,

        )

    