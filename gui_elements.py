import time

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QBrush, QColor, QFont
from PyQt6.QtWidgets import (QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsTextItem,
                             QSpinBox, QLineEdit)


class LineBetween(QGraphicsLineItem):
    """GUI line between given points."""

    def __init__(self, x, y, x_end, y_end, color="#000000", dashed=False, width=1, layer=0):
        super().__init__(x, y, x_end, y_end)

        self.setZValue(layer)
        pen = QPen(QColor(color))
        pen.setWidth(width)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)  # Set dashed line style
        self.setPen(pen)


class CenteredCircle(QGraphicsEllipseItem):
    """GUI circle centered on given point."""

    def __init__(self, x, y, diameter, source_id=None, parent_scene=None, outline_width=1, outline_color="#000000",
                 dashed=False, fill_color=None, layer=0):
        super(CenteredCircle, self).__init__(x - diameter / 2, y - diameter / 2, diameter, diameter)

        self.setZValue(layer)
        self.source_id = source_id
        self.parent_scene = parent_scene

        if fill_color is not None:
            self.setBrush(QBrush(QColor(fill_color)))  # Apply fill color

        # Apply outline settings
        pen = QPen(QColor(outline_color))
        pen.setWidth(outline_width)
        if dashed:
            pen.setStyle(Qt.PenStyle.DashLine)  # Set dashed line style
        self.setPen(pen)

    def mousePressEvent(self, event):
        """Handles clicking on the GUI element."""

        if self.source_id is not None:
            for menu_item in self.parent_scene.menu_items:
                if menu_item[0] == self.source_id:
                    menu_item[2].toggle()   # Toggle source visibility checkmark
                    break
        else:
            event.ignore()


class Text(QGraphicsTextItem):
    """GUI text element."""

    def __init__(self, x, y, text, font_size=12, color="#FFFFFF", alignment=0, layer=0):
        super().__init__(text)

        self.setZValue(layer)
        self.setDefaultTextColor(QColor(color))  # Set text color

        # Set font size
        font = QFont()
        font.setPointSize(font_size)
        self.setFont(font)

        # Get text size and center it
        text_rect = self.boundingRect()
        if alignment == 0:
            self.setPos(x - text_rect.width() / 2, y - text_rect.height() / 2)
        elif alignment == -1:
            self.setPos(x, y - text_rect.height() / 2)
        elif alignment == 1:
            self.setPos(x - text_rect.width(), y - text_rect.height() / 2)


class IntegerSelector(QSpinBox):
    """GUI widget for integer selection."""

    def __init__(self, min_val=0, max_val=10):
        super().__init__()

        self.setMinimum(min_val)
        self.setMaximum(max_val)
        self.lineEdit().setReadOnly(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def wheelEvent(self, event):
        """Handles scrolling with GUI element selected."""

        event.ignore()

    def keyPressEvent(self, event):
        """Handles key presses with GUI element selected."""

        event.ignore()


class TextInput(QLineEdit):
    """GUI widget for text input."""

    def __init__(self, width=150, height=30, max_length=100, font_size=12, parent_scene=None):
        super().__init__()
        self.setFixedSize(width, height)  # Set fixed width and height
        self.setMaxLength(max_length)
        default_font = self.font()
        default_font.setPointSize(font_size)
        self.setFont(default_font)
        self.parent_scene = parent_scene

    def keyPressEvent(self, event):
        """Handles key presses with input field selected."""

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            try:
                self.parent_scene.local_time = time.mktime(time.strptime(self.text(), "%Y-%m-%d %H:%M"))
                self.parent_scene.update_time()
            except:
                print("Invalid time!")
                self.setText(time.strftime("%Y-%m-%d %H:%M", time.localtime(self.parent_scene.local_time)))

        else:
            super().keyPressEvent(event)
