# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal,QThread, QRectF
from PyQt5.QtWidgets import QFileDialog, QShortcut, QGraphicsPathItem
from PyQt5.QtGui import QTextCharFormat, QColor, QTextOption, QTransform, QPen, QPainterPath, QBrush
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView
from PyQt5.Qt import Qt
import sys
import json

import Aistant_IDE_UI
import Aistant_IDE_setting_manage
import openai
import threading
import logging
import os

log_num = 0
for file in os.listdir():
    if file.endswith(".log"):
        log_num += 1
log_name = "aistant_ide_" + str(log_num) + ".log"
print("log_name: ", log_name)
logging.basicConfig(filename=log_name, level=logging.INFO)

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
    def __init__(self, x, y, width, height, color, idx):
        super().__init__()
        self.idx = idx
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.setFlag(QGraphicsItem.ItemIsMovable)

    def boundingRect(self):
        return QRectF(self.x, self.y, self.width, self.height)

    def paint(self, painter, option, widget):
        print("Block:paint")
        # painter.fillRect(self.boundingRect(), self.color)
        pen = QPen(Qt.black)
        pen.setWidth(2)
        brush = QBrush(Qt.transparent)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRect(self.boundingRect())

class Connection(QGraphicsPathItem):
    def __init__(self, start_item, end_item):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.setPen(QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    def update_path(self):
        start_pos = self.mapFromItem(self.start_item, self.start_item.width / 2, self.start_item.height / 2)
        end_pos = self.mapFromItem(self.end_item, self.end_item.width / 2, self.end_item.height / 2)
        path = QPainterPath(start_pos)
        path.lineTo(end_pos)
        self.setPath(path)

    def paint(self, painter, option, widget):
        self.update_path()


class DiagramScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.item_moving = False
        self.start_item = None
        self.end_item = None
        self.connection = None

    def mousePressEvent(self, event):
        print("DiagramScene:mousePressEvent")
        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, Block):
            self.item_moving = True
            self.start_item = item
            self.connection = Connection(self.start_item, self.start_item)
            self.addItem(self.connection)
        else:
            self.item_moving = False
            self.start_item = None
            self.end_item = None
            self.connection = None

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        print("DiagramScene:mouseMoveEvent")
        if self.item_moving:
            super().mouseMoveEvent(event)
            self.connection.update_path()

    def mouseReleaseEvent(self, event):
        print("DiagramScene:mouseReleaseEvent")
        if self.item_moving:
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, Block) and item != self.start_item:
                self.end_item = item
                self.connection.end_item = self.end_item
                self.connection.update_path()
            else:
                self.removeItem(self.connection)

        self.item_moving = False
        self.start_item = None
        self.end_item = None
        self.connection = None

        super().mouseReleaseEvent(event)

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

        self.aistant_default_block_geo_config = (0, 0, 120, 50)
        self.current_block = Block(self.aistant_default_block_geo_config[0], 
                                   self.aistant_default_block_geo_config[1], 
                                   self.aistant_default_block_geo_config[2], 
                                   self.aistant_default_block_geo_config[3], Qt.black, self.current_agent_idx)
        self.aistant_y_delta = 0

        self.current_agent_block_item = {'block': self.current_block, 'block_setting': self.agent_setting}
        self.agent_block_setting_list = []
        self.agent_block_setting_list.append(self.current_agent_block_item)

        self.current_agent_num = len(self.agent_block_setting_list)

        self.statusbar_writer = Writer()
        self.statusbar_writer.write_signal.connect(self.ui.statusbar.showMessage)
        self.ui.statusbar.showMessage('Load Aistant IDE completed.')

        self.aistant_agent_output_writer = Writer()
        self.aistant_agent_output_writer.write_signal.connect(self.aistant_agent_output_stream_display_exec)

        self.aistant_public_output_writer = Writer()
        self.aistant_public_output_writer.write_signal.connect(self.aistant_public_display_exec)

        self.aistant_agent_working_flag = True

        self.aistant_agent_req_thread = AistantThread(self.Aistant_IDE_agent_block_exec)
        self.aistant_agent_req_thread.signal.connect(self.aistant_agent_update_ui_with_output)
        
        self.ui.pushButton_5.clicked.connect(self.aistant_public_update_keyword_exec)
        self.ui.pushButton_7.clicked.connect(self.aistant_public_mask_keyword_toggle_exec)

        self.ui.pushButton_6.clicked.connect(self.aistant_public_setting_show_toggle_exec)
        self.aistant_show_public_setting_status = False

        self.ui.pushButton_4.clicked.connect(self.aistant_clear_public_output_exec)

        self.ui.pushButton.clicked.connect(self.aistant_create_agent_exec)
        self.ui.pushButton_3.clicked.connect(self.aistant_remove_agent_exec)

# initial graphic view
        self.aistant_graphics_scene = DiagramScene()
        self.ui.graphicsView.setScene(self.aistant_graphics_scene)
        self.aistant_graphics_scene.addItem(self.current_block)

# update public environment setting(openai, etc, ...)
        cur_public_key = self.public_setting.aistant_setting_public_get_cur_key_val()
        if cur_public_key != '':
            openai.api_key = cur_public_key
            print("[Init]openai api key update: ", openai.api_key)
        else:
            print("[Init]openai api key empty.")

        self.aistant_password_mode = True
        self.ui.lineEdit_3.setText(openai.api_key)

    # show main window
    def Aistant_IDE_show(self):
        self.mainwin.show()

    def aistant_agent_update_ui_with_output(self, content):
        print("aistant_agent_update_ui_with_output: ", content)

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
    
    def aistant_public_UI_update(self, content_in):
        print('aistant_public_UI_update')
        final_output = '\n' + self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_agent_name + '\n' + content_in + '\n'
        # put final output to log
        logging.info(final_output)
        self.aistant_public_output_writer.write_signal.emit(final_output)
    
    def aistant_public_display_exec(self, content):
        cursor = self.ui.textEdit_2.textCursor()
        cursor.setPosition(len(self.ui.textEdit_2.toPlainText()))
        cursor.insertText(content)
        cursor.setPosition(len(self.ui.textEdit_2.toPlainText()))
        self.ui.textEdit_2.setTextCursor(cursor)

    def aistant_public_update_keyword_exec(self):
        print('aistant_public_update_keyword_exec')
        keyword = self.ui.lineEdit_3.text()
        if keyword == '':
            print('keyword is empty')
            return
        openai.api_key = keyword
        self.public_setting.aistant_setting_public_set_cur_key_val(keyword)
        print('update keyword: ', keyword)

    def aistant_public_mask_keyword_toggle_exec(self):
        print('aistant_public_mask_keyword_toggle_exec')
        if self.aistant_password_mode == True:
            self.ui.lineEdit_3.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.ui.pushButton_7.setText('Mask')
            self.aistant_password_mode = False
        else:
            self.ui.lineEdit_3.setEchoMode(QtWidgets.QLineEdit.Password)
            self.ui.pushButton_7.setText('Unmask')
            self.aistant_password_mode = True

    def aistant_public_setting_show_toggle_exec(self):
        print('aistant_public_setting_show_toggle_exec')
        if self.aistant_show_public_setting_status == False:
            self.ui.label_9.setVisible(True)
            self.ui.label_10.setVisible(True)
            self.ui.textEdit_3.setVisible(True)
            self.ui.label_7.setVisible(True)
            self.ui.lineEdit_3.setVisible(True)
            self.ui.pushButton_5.setVisible(True)
            self.ui.pushButton_7.setVisible(True)
            self.ui.pushButton_6.setText('Hide')
            self.aistant_show_public_setting_status = True
        else:
            self.ui.label_9.setVisible(False)
            self.ui.label_10.setVisible(False)
            self.ui.textEdit_3.setVisible(False)
            self.ui.label_7.setVisible(False)
            self.ui.lineEdit_3.setVisible(False)
            self.ui.pushButton_5.setVisible(False)
            self.ui.pushButton_7.setVisible(False)
            self.ui.pushButton_6.setText('Show')
            self.aistant_show_public_setting_status = False

    def aistant_clear_public_output_exec(self):
        print('aistant_clear_public_output_exec')
        self.ui.textEdit_2.clear()

    def aistant_create_agent_exec(self):
        print('aistant_create_agent_exec')
        self.current_agent_num = len(self.agent_block_setting_list)
        self.aistant_y_delta += (self.aistant_default_block_geo_config[3] + 5)
        new_block = Block(  self.aistant_default_block_geo_config[0], 
                            self.aistant_default_block_geo_config[1] + self.aistant_y_delta, 
                            self.aistant_default_block_geo_config[2], 
                            self.aistant_default_block_geo_config[3], Qt.black, self.current_agent_num)
        self.aistant_graphics_scene.addItem(new_block)
        new_setting = Aistant_IDE_setting_manage.Aistant_Agent_Setting()

        new_agent_block_item = {'block': new_block, 'block_setting': new_setting}
        self.agent_block_setting_list.append(new_agent_block_item)
        
    def aistant_remove_agent_exec(self):
        print('aistant_remove_agent_exec')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    aistant_ide_ui = Aistant_IDE()
    aistant_ide_ui.Aistant_IDE_show()
    sys.exit(app.exec_())