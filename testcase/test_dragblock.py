from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

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
        if self.item_moving:
            super().mouseMoveEvent(event)
            self.connection.update_path()

    def mouseReleaseEvent(self, event):
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

if __name__ == '__main__':
    app = QApplication([])
    view = QGraphicsView()
    scene = DiagramScene()
    view.setScene(scene)
    view.show()

    block1 = Block(0, 0, 100, 100, Qt.red)
    block2 = Block(200, 200, 100, 100, Qt.blue)
    scene.addItem(block1)
    scene.addItem(block2)

    app.exec_()