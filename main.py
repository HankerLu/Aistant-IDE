# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QObject, pyqtSignal,QThread, QRectF, QPointF
from PyQt5.QtWidgets import QFileDialog, QShortcut, QGraphicsPathItem, QGraphicsTextItem
from PyQt5.QtGui import QTransform, QPen, QPainterPath, QBrush, QDoubleValidator, QIntValidator, QFont
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
import math

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
        print("Block:__init__", idx)
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
        # print("Block:paint", self.idx)
        # painter.fillRect(self.boundingRect(), self.color)
        pen = QPen(Qt.black)
        pen.setWidth(2)
        brush = QBrush(Qt.transparent)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRect(self.boundingRect())

# class Connection(QGraphicsPathItem):
#     def __init__(self, start_item, end_item):
#         super().__init__()
#         print("Connection:__init__")
#         self.start_item = start_item
#         self.end_item = end_item
#         self.setPen(QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

#     def update_path(self):
#         start_pos = self.mapFromItem(self.start_item, self.start_item.width / 2, self.start_item.height / 2)
#         end_pos = self.mapFromItem(self.end_item, self.end_item.width / 2, self.end_item.height / 2)
#         end_pos = self.mapFromItem(self.end_item, self.end_item.width / 4, self.end_item.height / 4)
#         path = QPainterPath(start_pos)
#         path.lineTo(end_pos)
#         self.setPath(path)
#         print("Connection:update_path", start_pos, end_pos)

#     def paint(self, painter, option, widget):
#         self.update_path()

class ConnectionLine(QGraphicsPathItem):
    def __init__(self, start_item, end_item, parent=None):
        super(ConnectionLine, self).__init__(parent)
        self.start_item = start_item
        self.end_item = end_item
        self.setZValue(-1)
        
        self.update_path()
        
    def update_path(self):
        path = QPainterPath(self.start_item.pos())
        path.lineTo(self.end_item.pos())
        
        # 添加箭头
        arrow_size = 10
        angle = self.line_angle()
        arrow_p1 = self.end_item.pos() + QPointF(math.sin(angle - math.pi / 3) * arrow_size,
                                                 math.cos(angle - math.pi / 3) * arrow_size)
        arrow_p2 = self.end_item.pos() + QPointF(math.sin(angle - math.pi + math.pi / 3) * arrow_size,
                                                 math.cos(angle - math.pi + math.pi / 3) * arrow_size)
        path.moveTo(self.end_item.pos())
        path.lineTo(arrow_p1)
        path.moveTo(self.end_item.pos())
        path.lineTo(arrow_p2)
        
        self.setPath(path)
        
    def line_angle(self):
        dx = self.end_item.pos().x() - self.start_item.pos().x()
        dy = self.end_item.pos().y() - self.start_item.pos().y()
        angle = math.atan2(-dy, dx)
        return angle
    
class DiagramScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(None)
        self.item_moving = False
        self.line_painting = False
        self.start_item = None
        self.end_item = None
        self.connection = None
        self.last_clicked_item_idx = 0
        self.parent = parent

    def mousePressEvent(self, event):
        # print("DiagramScene:mousePressEvent", event.scenePos())
        item = self.itemAt(event.scenePos(), QTransform())
        if isinstance(item, QGraphicsTextItem):
            item = item.parentItem()
            print("QGraphicsTextItem: ", item.idx)
            if self.parent.current_agent_idx != item.idx:
                self.parent.current_agent_idx = item.idx
                self.parent.aistant_update_agent_UI()
                # self.parent.agent_setting.update_agent_setting()
            self.last_clicked_item_idx = item.idx
            self.item_moving = True
            self.start_item = item
            self.connection = ConnectionLine(self.start_item, self.start_item)
            self.addItem(self.connection)
        elif isinstance(item, Block):
            print("isinstance(item, Block): ", item.idx)
            pos = event.pos()
            distances = [
                abs(pos.x() - item.boundingRect().left()),
                abs(pos.x() - item.boundingRect().right()),
                abs(pos.y() - item.boundingRect().top()),
                abs(pos.y() - item.boundingRect().bottom())
            ]
            min_distance = min(distances)

            if min_distance < 15:
                print("Clicked near the edge")
                self.item_moving = False
                self.start_item = item
                self.end_item = None
                self.connection = None
                self.line_painting = True
            else:
                print("Clicked inside the item")
                self.item_moving = False
                self.start_item = None
                self.end_item = None
                self.connection = None

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.item_moving:
            # print("DiagramScene:mouseMoveEvent")
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
        
# set floating point validator
        self.ui.lineEdit_2.setValidator(QDoubleValidator(0.0, 1.0, 2))
        self.ui.lineEdit_4.setValidator(QIntValidator(0, 500))
       
        self.ui.pushButton_5.clicked.connect(self.aistant_public_update_keyword_exec)
        self.ui.pushButton_7.clicked.connect(self.aistant_public_mask_keyword_toggle_exec)

        self.ui.pushButton_6.clicked.connect(self.aistant_public_setting_show_toggle_exec)

        self.ui.pushButton_4.clicked.connect(self.aistant_clear_public_output_exec)

        self.ui.pushButton.clicked.connect(self.aistant_create_agent_exec)
        self.ui.pushButton_3.clicked.connect(self.aistant_remove_agent_exec)

        self.ui.pushButton_12.clicked.connect(self.aistant_agent_save_config_from_ui_exec)
        self.ui.pushButton_2.clicked.connect(self.aistant_agent_load_config_from_default_exec)

# init toggle execution
        self.aistant_show_public_setting_status = False
        self.aistant_password_mode = True
        self.aistant_public_setting_show_toggle_exec()
        self.aistant_public_mask_keyword_toggle_exec()

# initial graphic view
        self.aistant_graphics_scene = DiagramScene(self)
        self.ui.graphicsView.setScene(self.aistant_graphics_scene)
        self.aistant_graphics_scene.addItem(self.current_block)

        text_item_content = self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_agent_name
        text_item = QGraphicsTextItem(text_item_content)
        text_item.setDefaultTextColor(Qt.black)
        text_item.setFont(QFont('Arial', 12))
        self.aistant_graphics_scene.addItem(text_item)
        text_item.setParentItem(self.current_block)
        text_item.setX(self.current_block.boundingRect().center().x() - text_item.boundingRect().width()/2)
        text_item.setY(self.current_block.boundingRect().center().y() - text_item.boundingRect().height()/2)

        self.aistant_update_agent_UI()

# update public environment setting(openai, etc, ...)
        cur_public_key = self.public_setting.aistant_setting_public_get_cur_key_val()
        if cur_public_key != '':
            openai.api_key = cur_public_key
            print("[Init]openai api key update: ", openai.api_key)
        else:
            print("[Init]openai api key empty.")

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
        self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_tempory_output_content = self.ui.textEdit.toPlainText()

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
        new_setting_name = 'Agent_' + str(self.current_agent_num)
        new_setting = Aistant_IDE_setting_manage.Aistant_Agent_Setting(new_setting_name)

        new_agent_block_item = {'block': new_block, 'block_setting': new_setting}
        self.agent_block_setting_list.append(new_agent_block_item)

        text_item_content = new_setting_name
        text_item = QGraphicsTextItem(text_item_content)
        text_item.setDefaultTextColor(Qt.black)
        text_item.setFont(QFont('Arial', 12))
        self.aistant_graphics_scene.addItem(text_item)
        text_item.setParentItem(new_block)
        text_item.setX(new_block.boundingRect().center().x() - text_item.boundingRect().width()/2)
        text_item.setY(new_block.boundingRect().center().y() - text_item.boundingRect().height()/2)

    def aistant_remove_agent_exec(self):
        print('aistant_remove_agent_exec')

#update agent UI display
    def aistant_update_agent_UI(self):
        print('aistant_update_agent_UI')
        tempeture_str = str(self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_tempeture)
        max_tokens_str = str(self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_max_token)
        self.ui.lineEdit.setText(self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_agent_name)
        self.ui.comboBox_4.setCurrentIndex(self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_model_index)
        self.ui.plainTextEdit.setPlainText(self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_function_prompt)
        self.ui.lineEdit_2.setText(tempeture_str)
        self.ui.lineEdit_4.setText(max_tokens_str)
        self.ui.lineEdit_5.setText(self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_extern_link)
        self.ui.textEdit.setPlainText(self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_tempory_output_content)

    def aistant_agent_save_config_from_ui_exec(self):
        print('aistant_agent_save_config_from_ui_exec')
        try:
            temperatue_lineedit_content = self.ui.lineEdit_2.text()
            max_token_lineedit_content = self.ui.lineEdit_4.text()
            if temperatue_lineedit_content == '' or max_token_lineedit_content == '':
                self.statusbar_writer.write_signal.emit('Please fill in valid num for tempeture and max tokens')
                return

            self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_agent_name = self.ui.lineEdit.text()
            self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_model_index = self.ui.comboBox_4.currentIndex()
            self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_function_prompt = self.ui.plainTextEdit.toPlainText()
            self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_tempeture = float(self.ui.lineEdit_2.text())
            self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_max_token = int(self.ui.lineEdit_4.text())
            self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_extern_link = self.ui.lineEdit_5.text()
            self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_tempory_output_content = self.ui.textEdit.toPlainText()
        except Exception as e:
            print('save config error. Error: ', e)

    def aistant_agent_load_config_from_default_exec(self):
        print('aistant_agent_load_config_from_default_exec')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    aistant_ide_ui = Aistant_IDE()
    aistant_ide_ui.Aistant_IDE_show()
    sys.exit(app.exec_())