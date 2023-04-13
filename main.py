# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal,QThread
from PyQt5.QtWidgets import QFileDialog, QShortcut
from PyQt5.QtGui import QTextCharFormat, QColor, QTextOption
from PyQt5.Qt import Qt
import sys
import json

import Aistant_IDE_UI
import Aistant_IDE_setting_manage
import openai
import threading
import logging

class Aistant_IDE(Aistant_IDE_UI.Ui_MainWindow):
    def __init__(self) -> None:
        print("Aistant_IDE init")
        Mainwindw = QtWidgets.QMainWindow()
        ui = Aistant_IDE_UI.Ui_MainWindow()
        ui.setupUi(Mainwindw)

        self.mainwin = Mainwindw
        self.ui = ui

        self.setting = Aistant_IDE_setting_manage.Aistant_IDE_setting_manage()