# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal,QThread, QRectF
from PyQt5.QtWidgets import QFileDialog, QShortcut
from PyQt5.QtGui import QTextCharFormat, QColor, QTextOption
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView
from PyQt5.Qt import Qt
import sys
import json

import Aistant_IDE_UI
import Aistant_IDE_setting_manage
import openai
import threading
import logging

class Writer(QObject):
    write_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def write_to_display_widget(self, text):
        self.write_signal.emit(text)

class AistantThread(QThread):
    # 定义一个信号，用于在线程中发射信号
    signal = pyqtSignal(str)
    signal_int = pyqtSignal(int)
    def __init__(self, handle, parent=None):
        super(AistantThread, self).__init__(parent)
        self.run_handle = handle
    
    def run(self):
        # 在线程中执行长时间操作
        if self.run_handle != None:
            ret = self.run_handle()
            
            print("AistantThread:run_handle. RET: ", ret)
            self.signal.emit(ret)
    
    def signal_emit(self, val):
        self.signal_int.emit(val)

class Block(QGraphicsItem):
    def __init__(self, x, y, width, height, color):
        super().__init__()
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def boundingRect(self):
        return QRectF(self.x, self.y, self.width, self.height)

    def paint(self, painter, option, widget):
        painter.fillRect(self.boundingRect(), self.color)

class Aistant_IDE(Aistant_IDE_UI.Ui_MainWindow):
    def __init__(self) -> None:
        print("Aistant_IDE init")
        Mainwindw = QtWidgets.QMainWindow()
        ui = Aistant_IDE_UI.Ui_MainWindow()
        ui.setupUi(Mainwindw)

        self.mainwin = Mainwindw
        self.ui = ui

        self.agent_setting = Aistant_IDE_setting_manage.Aistant_Agent_Setting()

        self.public_setting = Aistant_IDE_setting_manage.Aistant_Public_Setting()

        self.current_agent_idx = 0
        
        self.current_block = Block(0, 0, 100, 100, Qt.red)
        self.current_agent_block_item = {'block': self.current_block, 'block_setting': self.agent_setting}
        self.agent_block_setting_list = []
        self.agent_block_setting_list.append(self.current_agent_block_item)

        self.statusbar_writer = Writer()
        self.statusbar_writer.write_signal.connect(self.ui.statusbar.showMessage)
        self.ui.statusbar.showMessage('Load Aistant IDE completed.')

        self.aistant_agent_output_writer = Writer()
        self.aistant_agent_output_writer.write_signal.connect(self.aistant_agent_output_stream_display_exec)

        self.aistant_agent_working_flag = True


        self.aistant_agent_req_thread = AistantThread(self.Aistant_IDE_agent_block_exec)
        self.aistant_agent_req_thread.signal.connect(self.aistant_agent_update_ui_with_output)


    # show main window
    def Aistant_IDE_show(self):
        self.mainwin.show()

    def aistant_agent_output_stream_display_exec(self, content):
        cursor = self.ui.textEdit.textCursor()
        cursor.setPosition(len(self.ui.textEdit.toPlainText()))
        cursor.insertText(content)
        cursor.setPosition(len(self.ui.textEdit.toPlainText()))
        self.ui.textEdit.setTextCursor(cursor)

    def aistant_agent_req_trig(self):
        print('aistant_agent_req_trig')
        self.aistant_agent_req_thread.start()

    def Aistant_IDE_agent_block_exec(self, content_in):
        prompt_in = self.agent_setting.aistant_ide_function_prompt + content_in
        self.aistant_agent_working_flag = True
        self.Aistant_IDE_stream_openai_api_req(prompt_in)

    def Aistant_IDE_stream_openai_api_req(self, prompt_in):
        self.statusbar_writer.write_signal.emit('openai request start.')
        agent_req_total_messages = []
        try:
            user_question = {"role": "user", "content": ""}
            user_question['content'] = prompt_in
            agent_req_total_messages.append(user_question) # 新增 
            print('before openai.ChatCompletion.create')
            self.editor_req_stream_res = openai.ChatCompletion.create(
            model = 'gpt-3.5-turbo',
            messages = agent_req_total_messages,
            temperature = self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_temperature,
            max_tokens = self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_max_tokens,
            stream=True
            )
            self.aistant_agent_output_writer.write_signal.emit('\n')

            try:
                for chunk in self.editor_req_stream_res:
                    chunk_message = chunk['choices'][0]['delta']  # extract the message
                    single_msg = chunk_message.get('content', '')
                    # self.aistant_improve_thread.signal.emit(single_msg)
                    self.aistant_agent_output_writer.write_signal.emit(single_msg)
                    print(single_msg)
                    if self.aistant_agent_working_flag == False:
                        print('aistant_agent_working_flag is False, break.')
                        break
            except Exception as e:
                pass
            self.statusbar_writer.write_signal.emit('Agent output stream end.')
            
        except Exception as e:
            logging.info("aistant_stream_openai_api_req error")
            print("aistant_stream_openai_api_req error", e)
            self.statusbar_writer.write_signal.emit('Agent output stream error.')
        
        if self.aistant_agent_working_flag == False:
            self.aistant_agent_working_flag = True
            self.statusbar_writer.write_signal.emit('Agent output stream quit.')
        return ''