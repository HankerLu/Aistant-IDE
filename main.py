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
from enum import Enum

log_num = 0
for file in os.listdir():
    if file.endswith(".log"):
        log_num += 1
log_name = "aistant_ide_" + str(log_num) + ".log"
print("log_name: ", log_name)
logging.basicConfig(filename=log_name, level=logging.INFO)

class AistantWorkFlowStatus(Enum):
    WF_IDLE = 0
    WF_EXEC = 1
    WF_DONE = 2
    WF_STOP = 3

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
        self.input_idx_list = []
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

    def reg_new_input(self, input_idx):
        self.input_idx_list.append(input_idx)

class Connection(QGraphicsPathItem):
    def __init__(self, start_item, end_item):
        super().__init__()
        print("Connection:__init__")
        self.start_item = start_item
        self.end_item = end_item
        self.setPen(QPen(Qt.black, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    def update_path(self):
        start_pos = self.mapFromItem(self.start_item, self.start_item.width / 2, self.start_item.height / 2)
        end_pos = self.mapFromItem(self.end_item, self.end_item.width / 2, self.end_item.height / 2)
        path = QPainterPath(start_pos)
        path.lineTo(end_pos)
        self.setPath(path)
        # print("Connection:update_path", start_pos, end_pos)

    def paint(self, painter, option, widget):
        self.update_path()

class LinePathWithArrow(QGraphicsPathItem):
    def __init__(self, start_item = None, end_item = None, parent=None):
        super(LinePathWithArrow, self).__init__(None)
        self.start_item = start_item
        self.end_item = end_item
        self.setZValue(-1)
        self.setPen(QPen(Qt.black, 3))
        self.parent = parent
    
    def set_start_edge(self, edge):
        self.start_edge = edge

    def set_end_edge(self, edge):
        self.end_edge = edge

    def get_start_point_pos(self):
        ret = self.start_item.pos()
        if self.start_edge == "left":
            ret = self.mapFromItem(self.start_item, 0, self.start_item.y + self.start_item.height / 2)
        elif self.start_edge == "right":
            ret = self.mapFromItem(self.start_item, self.start_item.width, self.start_item.y + self.start_item.height / 2)
        elif self.start_edge == "top":
            ret = self.mapFromItem(self.start_item, self.start_item.width / 2, self.start_item.y)
        elif self.start_edge == "bottom":
            ret = self.mapFromItem(self.start_item, self.start_item.width / 2, self.start_item.y + self.start_item.height)
        return ret
    
    def get_end_point_pos(self):
        ret = self.end_item.pos()
        if self.end_edge == "left":
            ret = self.mapFromItem(self.end_item, 0, self.end_item.y + self.end_item.height / 2)
        elif self.end_edge == "right":
            ret = self.mapFromItem(self.end_item, self.end_item.width, self.end_item.y + self.end_item.height / 2)
        elif self.end_edge == "top":
            ret = self.mapFromItem(self.end_item, self.end_item.width / 2, self.end_item.y)
        elif self.end_edge == "bottom":
            ret = self.mapFromItem(self.end_item, self.end_item.width / 2, self.end_item.y + self.end_item.height)
        return ret

    def update_path_with_both_item(self):
        if self.start_item is None or self.end_item is None:
            return
        tmp_start_pos = self.get_start_point_pos()
        tmp_end_pos = self.get_end_point_pos()
        path = QPainterPath(tmp_start_pos)
        path.lineTo(tmp_end_pos)
        
        # 添加箭头
        arrow_size = 10
        dx = tmp_end_pos.x() - tmp_start_pos.x()
        dy = tmp_end_pos.y() - tmp_start_pos.y()
        angle = math.atan2(-dy, dx)
        arrow_p1 = tmp_end_pos + QPointF(math.sin(angle - math.pi / 3) * arrow_size,
                                                 math.cos(angle - math.pi / 3) * arrow_size)
        arrow_p2 = tmp_end_pos + QPointF(math.sin(angle - math.pi + math.pi / 3) * arrow_size,
                                                 math.cos(angle - math.pi + math.pi / 3) * arrow_size)
        path.moveTo(tmp_end_pos)
        path.lineTo(arrow_p1)
        path.moveTo(tmp_end_pos)
        path.lineTo(arrow_p2)
        
        self.setPath(path)

    def update_path_by_end_pos(self, end_pos):        
        tmp_start_pos = self.get_start_point_pos()
        path = QPainterPath(tmp_start_pos)
        path.lineTo(end_pos)
        
        # 添加箭头
        arrow_size = 10
        dx = end_pos.x() - tmp_start_pos.x()
        dy = end_pos.y() - tmp_start_pos.y()
        angle = math.atan2(-dy, dx)
        arrow_p1 = end_pos + QPointF(math.sin(angle - math.pi / 3) * arrow_size,
                                                 math.cos(angle - math.pi / 3) * arrow_size)
        arrow_p2 = end_pos + QPointF(math.sin(angle - math.pi + math.pi / 3) * arrow_size,
                                                 math.cos(angle - math.pi + math.pi / 3) * arrow_size)
        path.moveTo(end_pos)
        path.lineTo(arrow_p1)
        path.moveTo(end_pos)
        path.lineTo(arrow_p2)
        
        self.setPath(path)
    
    def set_end_item(self, item):
        self.end_item = item
        self.end_item.reg_new_input(self.start_item.idx)
    
    def update_start_edge(self, e_pos):
        item_pos = self.mapFromItem(self.start_item, self.start_item.x, self.start_item.y)
        item_edge_left = item_pos.x()
        item_edge_right = item_pos.x() + self.start_item.width
        item_edge_top = item_pos.y()
        item_edge_bottom = item_pos.y() + self.start_item.height
        print("---------", 
                item_edge_left, item_edge_right, item_edge_top, item_edge_bottom,
                item_pos.x(), item_pos.y(), self.start_item.width, self.start_item.height)
        distances = [
            abs(e_pos.x() - item_edge_left),
            abs(e_pos.x() - item_edge_right),
            abs(e_pos.y() - item_edge_top),
            abs(e_pos.y() - item_edge_bottom)
        ]
        for i in range(len(distances)):
            print(distances[i])
        min_distance = min(distances)
        # find the closest edge
        if min_distance == distances[0]:
            print("Clicked near the left edge")
            self.set_start_edge("left")
        elif min_distance == distances[1]:
            print("Clicked near the right edge")
            self.set_start_edge("right")
        elif min_distance == distances[2]:
            print("Clicked near the top edge")
            self.set_start_edge("top")
        elif min_distance == distances[3]:
            print("Clicked near the bottom edge")
            self.set_start_edge("bottom")

    def update_end_edge(self, e_pos):
        item_pos = self.mapFromItem(self.end_item, self.end_item.x, self.end_item.y)
        item_edge_left = item_pos.x()
        item_edge_right = item_pos.x() + self.end_item.width
        item_edge_top = item_pos.y()
        item_edge_bottom = item_pos.y() + self.end_item.height
        print("---------", 
                item_edge_left, item_edge_right, item_edge_top, item_edge_bottom,
                item_pos.x(), item_pos.y(), self.end_item.width, self.end_item.height)
        distances = [
            abs(e_pos.x() - item_edge_left),
            abs(e_pos.x() - item_edge_right),
            abs(e_pos.y() - item_edge_top),
            abs(e_pos.y() - item_edge_bottom)
        ]
        for i in range(len(distances)):
            print(distances[i])
        min_distance = min(distances)
        # find the closest edge
        if min_distance == distances[0]:
            print("Released near the left edge")
            self.set_end_edge("left")
        elif min_distance == distances[1]:
            print("Released near the right edge")
            self.set_end_edge("right")
        elif min_distance == distances[2]:
            print("Released near the top edge")
            self.set_end_edge("top")
        elif min_distance == distances[3]:
            print("Released near the bottom edge")
            self.set_end_edge("bottom")

    def mousePressEvent(self, event):
        print("DiagramConnection:mousePressEvent")
        if self.contains(event.pos()):
            print("-----DiagramConnection:mousePressEvent:contains")
            # self.setPen(QPen(Qt.red, 2.5))
            # self.parent.cur_line_path_arrow = self
            self.parent.selectLinePathWithArrow(self)

class DiagramScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(None)
        self.line_connecting = False
        self.item_moving = False
        self.start_item = None
        self.end_item = None
        self.connection = None
        self.line_path_arrow = None
        self.last_clicked_item_idx = 0
        self.cur_line_path_arrow = None
        self.cur_line_path_arrow_reverse = None
        self.parent = parent

    def findReverseConnection(self, item_in):
        if item_in == None or type(item_in) != LinePathWithArrow:
            return None
        for item in self.items():
            if isinstance(item, LinePathWithArrow) \
            and item_in.start_item.idx == item.end_item.idx and item_in.end_item.idx == item.start_item.idx:
                return item
        return None

    def selectLinePathWithArrow(self, line_path_arrow):
        print("DiagramScene:selectLinePathWithArrow")
        self.cur_line_path_arrow = line_path_arrow
        self.cur_line_path_arrow.setPen(QPen(Qt.red, 4.0))
        self.cur_line_path_arrow_reverse = self.findReverseConnection(self.cur_line_path_arrow)
        if self.cur_line_path_arrow_reverse != None:
            print("DiagramScene:selectLinePathWithArrow:reverse found")
            self.cur_line_path_arrow_reverse.setPen(QPen(Qt.red, 4.0))
        for item in self.items():
            if isinstance(item, LinePathWithArrow):
                if item != self.cur_line_path_arrow and item != self.cur_line_path_arrow_reverse:
                    item.setPen(QPen(Qt.black, 3.0))

    def mousePressEvent(self, event):
        # print("DiagramScene:mousePressEvent")
        # print("DiagramScene:mousePressEvent", event.scenePos())
        item = self.itemAt(event.scenePos(), QTransform())
        # move item
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
            self.line_connecting = False
            self.connection = Connection(self.start_item, self.start_item)
            self.addItem(self.connection)                            
        # connect item
        elif isinstance(item, Block):
            print("isinstance(item, Block): ", item.idx)
            print("Clicked near the edge")
            self.item_moving = False
            self.start_item = None
            self.end_item = None
            self.connection = None
            self.line_connecting = True
            self.line_path_arrow = LinePathWithArrow(item, None, self)
            self.line_path_arrow.update_start_edge(event.scenePos())
            self.addItem(self.line_path_arrow)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.item_moving:
            # print("DiagramScene:mouseMoveEvent")
            super().mouseMoveEvent(event)
            self.connection.update_path()
            for item in self.items():
                if isinstance(item, LinePathWithArrow):
                    if item.start_item == self.start_item or item.end_item == self.start_item:
                        item.update_path_with_both_item()
        elif self.line_connecting:
            # print("DiagramScene:mouseMoveEvent: line_connecting")
            self.line_path_arrow.update_path_by_end_pos(event.scenePos())
            # self.connection.end_item = event.scenePos()
            # self.connection.update_path()

    def mouseReleaseEvent(self, event):
        print("DiagramScene:mouseReleaseEvent", event.scenePos())
        if self.item_moving:
            print("DiagramScene:mouseReleaseEvent: item_moving")
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, Block) and item != self.start_item:
                print("DiagramScene:mouseReleaseEvent: item_moving: isinstance(item, Block)")
                self.end_item = item
                self.connection.end_item = self.end_item
                self.connection.update_path()
            else:
                print("DiagramScene:mouseReleaseEvent: item_moving: not isinstance(item, Block)")
                self.removeItem(self.connection)
        # finish connecting line
        elif self.line_connecting == True:
            item = self.itemAt(event.scenePos(), QTransform())
            if isinstance(item, Block) and item != self.start_item:
                print("DiagramScene:mouseReleaseEvent: line_connecting: isinstance(item, Block)")
                if item.idx == self.line_path_arrow.start_item.idx:
                    print("end item is the same as start item.")
                    self.removeItem(self.line_path_arrow)
                    return
                
                for idx in item.input_idx_list:
                    if idx == self.line_path_arrow.start_item.idx:
                        print("line_path_arrow already exists.")
                        self.removeItem(self.line_path_arrow)
                        return
                self.line_path_arrow.set_end_item(item)
                self.line_path_arrow.update_end_edge(event.scenePos())
                self.line_path_arrow.update_path_with_both_item()
            else:
                print("DiagramScene:mouseReleaseEvent: line_connecting: not isinstance(item, Block)")
                self.removeItem(self.line_path_arrow)

        self.item_moving = False
        self.start_item = None
        self.end_item = None
        self.connection = None
        self.line_connecting = False
        self.line_path_arrow = None

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

        self.ui.pushButton_8.clicked.connect(self.aistant_remove_line_exec)

        self.ui.pushButton_9.clicked.connect(self.aistant_workflow_run_exec)
        self.ui.pushButton_10.clicked.connect(self.aistant_workflow_stop_exec)
        self.ui.pushButton_11.clicked.connect(self.aistant_workflow_reset_exec)

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

# AI workflow
        self.aistant_ide_workflow = []
        self.aistant_ide_workflow_pos = 0
        self.aistant_ide_workflow_item_num = 0
        self.aistant_ide_running_status = AistantWorkFlowStatus.WF_IDLE

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
            # self.ui.label_9.setVisible(True)
            self.ui.label_10.setVisible(True)
            self.ui.textEdit_3.setVisible(True)
            self.ui.label_7.setVisible(True)
            self.ui.lineEdit_3.setVisible(True)
            self.ui.pushButton_5.setVisible(True)
            self.ui.pushButton_7.setVisible(True)
            self.ui.pushButton_6.setText('Hide')
            self.aistant_show_public_setting_status = True
        else:
            # self.ui.label_9.setVisible(False)
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
        if self.current_agent_num == 0:
            print('no agent to remove')
            return
        self.aistant_y_delta -= (self.aistant_default_block_geo_config[3] + 5)
        self.aistant_graphics_scene.removeItem(self.agent_block_setting_list[self.current_agent_idx]['block'])
        # self.aistant_graphics_scene.removeItem(self.agent_block_setting_list[self.current_agent_num]['block'].text_item)
        # delete connection and patharrow of aistant_graphics_scene
        # for i in range(len(self.aistant_graphics_scene.items())):
        #     if type(self.aistant_graphics_scene.items()[i]) == Connection or type(self.aistant_graphics_scene.items()[i]) == LinePathWithArrow:
        #         if self.aistant_graphics_scene.items()[i].start_item == self.agent_block_setting_list[self.current_agent_num]['block'] \
        #         or self.aistant_graphics_scene.items()[i].end_item == self.agent_block_setting_list[self.current_agent_num]['block']:
        #             self.aistant_graphics_scene.removeItem(self.aistant_graphics_scene.items()[i])
        for item in self.aistant_graphics_scene.items(): 
            if type(item) == Connection or type(item) == LinePathWithArrow:
                if item.start_item == self.agent_block_setting_list[self.current_agent_idx]['block'] \
                or item.end_item == self.agent_block_setting_list[self.current_agent_idx]['block']:
                    self.aistant_graphics_scene.removeItem(item)
            elif type(item) == Block:
                for i in range(len(item.input_idx_list)):
                    if item.input_idx_list[i] == self.current_agent_idx:
                        item.input_idx_list[i] = -1
        self.agent_block_setting_list.pop(self.current_agent_idx)
        self.current_agent_num -= 1

#remove line 
    def aistant_remove_line_exec(self):
        print('aistant_remove_line_exec')
        if self.aistant_graphics_scene.cur_line_path_arrow != None:
            self.aistant_graphics_scene.cur_line_path_arrow.end_item.input_idx_list.remove(self.aistant_graphics_scene.cur_line_path_arrow.start_item.idx)
            self.aistant_graphics_scene.removeItem(self.aistant_graphics_scene.cur_line_path_arrow)
            self.aistant_graphics_scene.cur_line_path_arrow = None
        if self.aistant_graphics_scene.cur_line_path_arrow_reverse != None:
            self.aistant_graphics_scene.cur_line_path_arrow_reverse.end_item.input_idx_list.remove(self.aistant_graphics_scene.cur_line_path_arrow_reverse.start_item.idx)
            self.aistant_graphics_scene.removeItem(self.aistant_graphics_scene.cur_line_path_arrow_reverse)
            self.aistant_graphics_scene.cur_line_path_arrow_reverse = None
        
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
            
            self.agent_block_setting_list[self.current_agent_idx]['block'].childItems().pop(0).setPlainText(self.agent_block_setting_list[self.current_agent_idx]['block_setting'].aistant_ide_agent_name)

        except Exception as e:
            print('save config error. Error: ', e)

    def aistant_agent_load_config_from_default_exec(self):
        print('aistant_agent_load_config_from_default_exec')

    def aistant_workflow_run_exec(self):
        print('aistant_workflow_run_exec')
    
    def aistant_workflow_stop_exec(self):
        print('aistant_workflow_stop_exec')

    def aistant_workflow_reset_exec(self):
        print('aistant_workflow_reset_exec')

#workflow state machine
    def aistant_workflow_FSM(self):
        print('aistant_workflow_FSM')

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    aistant_ide_ui = Aistant_IDE()
    aistant_ide_ui.Aistant_IDE_show()
    sys.exit(app.exec_())