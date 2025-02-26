import calendar
import csv
import math
import sys
import os
import shutil
import time

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (QGraphicsScene, QGraphicsView, QApplication, QCheckBox, QGraphicsProxyWidget)

from gui_elements import LineBetween, CenteredCircle, Text, IntegerSelector, TextInput

SOURCE_FILE = "sources.csv"
CONFIG_FILE = "config.csv"

VERNAL_EQUINOX_UTC = "2025-03-20 09:01"     # UTC time of a vernal equinox
LST_FIX = -7.3 / 60  # Equation of time and unknown offset in hours


class GUIView(QGraphicsView):
    """GUI window handler."""

    def __init__(self, local_time):
        super().__init__()

        config = load_config()
        coordinates = (config[0], config[1])
        elevation_range = (config[2], config[3])
        window_size = (config[4], config[5])
        self.degree_scaling = config[6]

        # Instantiate GUI window
        self.scene = GUIScene(window_size, self.degree_scaling, elevation_range, local_time, coordinates)
        self.scene.setSceneRect(-window_size[0] / 2 * 0.99, -window_size[1] / 2 * 0.99,
                                window_size[0] * 0.99, window_size[1] * 0.99)
        self.setScene(self.scene)
        self.resize(window_size[0], window_size[1])
        self.setWindowTitle("Observation")

    def closeEvent(self, event):
        """Saves source list on exit."""

        if save_sources(self.scene.types, self.scene.sources):
            event.ignore()


class GUIScene(QGraphicsScene):
    """Scene used to hold all GUI elements."""

    def __init__(self, window_size, deg_scale, el_range, loc_time, coords):
        super(GUIScene, self).__init__()
        self.window_size = window_size
        self.degree_scaling = deg_scale
        self.elevation_range = el_range
        self.local_time = loc_time
        self.coordinates = coords
        
        self.types, self.sources = load_sources()

        # Add elevation circles
        for i in range(6):
            self.addItem(CenteredCircle(0, 0, (90 - 15 * i) * self.degree_scaling * 2,
                                        outline_width=1, outline_color="#A0A0A0", layer=-1))
            self.addItem(Text(0, -15 * (i + 1) * self.degree_scaling + 8, f"{90 - 15 * (i + 1)}°",
                              font_size=6, color="#A0A0A0", alignment=-1, layer=-1))

        # Add azimuth lines
        for i in range(12):
            x_end = math.cos(i * (2 * math.pi / 12)) * 90 * self.degree_scaling
            y_end = math.sin(i * (2 * math.pi / 12)) * 90 * self.degree_scaling
            self.addItem(LineBetween(0, 0, x_end, y_end, color="#A0A0A0", layer=-1))

        self.addItem(Text(0, -90 * self.degree_scaling - 10, "N", font_size=8, color="#A0A0A0", layer=-1))
        self.addItem(Text(0, 90 * self.degree_scaling + 10, "S", font_size=8, color="#A0A0A0", layer=-1))
        self.addItem(Text(-90 * self.degree_scaling - 10, 0, "E", font_size=8, color="#A0A0A0", layer=-1))
        self.addItem(Text(90 * self.degree_scaling + 10, 0, "W", font_size=8, color="#A0A0A0", layer=-1))

        self.addItem(CenteredCircle(0, 0, (90 - self.elevation_range[0]) * self.degree_scaling * 2,
                                    outline_width=3, outline_color="#FF0000"))
        self.addItem(CenteredCircle(0, 0, (90 - self.elevation_range[1]) * self.degree_scaling * 2,
                                    outline_width=2, dashed=True, outline_color="#FF0000"))

        # Add time menu
        time_start_position = (-self.window_size[0] / 2 + 80, -self.window_size[1] / 2 + 50)

        self.addItem(Text(time_start_position[0], time_start_position[1], "LOCAL",
                          alignment=1, font_size=12, color="#F0F0F0"))
        self.addItem(Text(time_start_position[0], time_start_position[1] + 30, "UTC",
                          alignment=1, font_size=12, color="#F0F0F0"))
        self.addItem(Text(time_start_position[0], time_start_position[1] + 60, "LST",
                          alignment=1, font_size=12, color="#F0F0F0"))

        proxy = QGraphicsProxyWidget()
        local_input_size = (140, 30)
        self.local_input = TextInput(local_input_size[0], local_input_size[1], max_length=19, font_size=12,
                                     parent_scene=self)
        self.local_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.local_input.setText(time.strftime("%Y-%m-%d %H:%M", time.localtime(self.local_time)))
        proxy.setWidget(self.local_input)
        proxy.setPos(time_start_position[0] + 10,
                     time_start_position[1] - local_input_size[1] / 2)
        self.addItem(proxy)

        self.utc_text = Text(time_start_position[0] + 15, time_start_position[1] + 30,
                             time.strftime("%Y-%m-%d %H:%M", time.gmtime(self.local_time)),
                             alignment=-1, font_size=12, color="#F0F0F0")
        self.lst_text = Text(time_start_position[0] + 15, time_start_position[1] + 60,
                             time.strftime("%Y-%m-%d %H:%M", local_to_lst(self.local_time, self.coordinates)),
                             alignment=-1, font_size=12, color="#F0F0F0")
        self.addItem(self.utc_text)
        self.addItem(self.lst_text)

        # Create source menu header
        menu_start_position = (self.window_size[0] / 2 - 120, -self.window_size[1] / 2 + 50)
        self.addItem(Text(menu_start_position[0], menu_start_position[1], "Source | Trace | Type",
                          font_size=12, color="#F0F0F0"))

        # Add source menu items
        self.menu_items = []
        # TODO: Add scrolling to support more than 18 sources
        for i in range(min(len(self.sources), 18)):
            name = Text(menu_start_position[0] - 20, menu_start_position[1] + 35 + i * 35, self.sources[i][0],
                        alignment=1, font_size=12, color="#F0F0F0")
            self.addItem(name)

            proxy = QGraphicsProxyWidget()
            checkbox = QCheckBox()
            checkbox.setChecked(self.sources[i][4])
            checkbox.stateChanged.connect(lambda state, index=i: self.on_selection_change(state, index))
            proxy.setWidget(checkbox)
            proxy.setPos(menu_start_position[0], menu_start_position[1] + 28 + i * 35)
            self.addItem(proxy)

            proxy = QGraphicsProxyWidget()
            int_selector = IntegerSelector(max_val=len(self.types) - 1)
            int_selector.setValue(self.sources[i][3])
            int_selector.valueChanged.connect(lambda value, index=i: self.on_value_change(value, index))
            proxy.setWidget(int_selector)
            proxy.setPos(menu_start_position[0] + 40, menu_start_position[1] + 24 + i * 35)
            self.addItem(proxy)

            self.menu_items.append((i, name, checkbox, int_selector))

        # Add objects from source list
        self.source_items = []
        for source in self.sources:
            # Draw object path
            path = CenteredCircle(0, -(90 - self.coordinates[0]) * self.degree_scaling,
                                  (90 - source[2]) * self.degree_scaling * 2,
                                  outline_width=1, dashed=True, outline_color="#00A000", layer=1)
            self.addItem(path)

            culmination_ratio = (source[1] - (local_to_lst(self.local_time, self.coordinates).tm_hour
                                              + local_to_lst(self.local_time, self.coordinates).tm_min / 60
                                              + local_to_lst(self.local_time, self.coordinates).tm_sec / 3600)) / 24

            x_offset = -math.sin(culmination_ratio * 2 * math.pi) * (90 - source[2]) * self.degree_scaling
            y_offset = math.cos(culmination_ratio * 2 * math.pi) * (90 - source[2]) * self.degree_scaling

            # Draw object
            marker = CenteredCircle(x_offset, -(90 - self.coordinates[0]) * self.degree_scaling + y_offset,
                                    self.types[source[3]][0], source_id=len(self.source_items), parent_scene=self,
                                    fill_color=self.types[source[3]][1], outline_width=1, outline_color="#000000",
                                    layer=2)
            self.addItem(marker)

            text = Text(x_offset, -(90 - self.coordinates[0]) * self.degree_scaling + y_offset + 15, f"{source[0]}",
                        font_size=8, color="#0000F0", layer=3)
            self.addItem(text)

            path.setVisible(source[4])
            text.setVisible(source[4])
            self.source_items.append((path, marker, text))

    def keyPressEvent(self, event):
        """Handles key presses."""

        if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.local_time -= 3600     # Rewind time by 1 hour
            self.update_time()
        elif event.key() in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.local_time += 3600     # Fast-forward time by 1 hour
            self.update_time()
        elif event.key() == Qt.Key.Key_Space:
            self.local_time = time.time()   # Reset to current time
            self.update_time()
        elif event.key() in (Qt.Key.Key_Up, Qt.Key.Key_W):
            # TODO: Scroll source list up
            pass
        elif event.key() in (Qt.Key.Key_Down, Qt.Key.Key_S):
            # TODO: Scroll source list down
            pass
        else:
            super().keyPressEvent(event)

    def on_selection_change(self, state, index):
        """Handles visibility selection changes via checkboxes."""

        if state == 2:
            state = 1

        self.source_items[self.menu_items[index][0]][0].setVisible(state)
        self.source_items[self.menu_items[index][0]][2].setVisible(state)
        self.sources[self.menu_items[index][0]][4] = state

    def on_value_change(self, value, index):
        """Handles type selection changes."""

        marker_rect = self.source_items[self.menu_items[index][0]][1].rect()
        marker_d = self.types[value][0]
        center_offset = (marker_d - marker_rect.width()) / 2
        self.source_items[self.menu_items[index][0]][1].setRect(marker_rect.x() - center_offset,
                                                                marker_rect.y() - center_offset,
                                                                marker_d, marker_d)
        self.source_items[self.menu_items[index][0]][1].setBrush(QBrush(QColor(self.types[value][1])))
        self.sources[self.menu_items[index][0]][3] = value

    def update_time(self):
        """Updates GUI elements affected by time selection."""

        self.local_input.setText(time.strftime("%Y-%m-%d %H:%M", time.localtime(self.local_time)))
        self.utc_text.setPlainText(time.strftime("%Y-%m-%d %H:%M", time.gmtime(self.local_time)))
        self.lst_text.setPlainText(time.strftime("%Y-%m-%d %H:%M", local_to_lst(self.local_time, self.coordinates)))

        for i in range(len(self.sources)):
            culmination_ratio = (self.sources[i][1] - (local_to_lst(self.local_time, self.coordinates).tm_hour
                                                       + local_to_lst(self.local_time, self.coordinates).tm_min / 60
                                                       + local_to_lst(self.local_time, self.coordinates).tm_sec / 3600)
                                 ) / 24

            x_offset = -math.sin(culmination_ratio * 2 * math.pi) * (90 - self.sources[i][2]) * self.degree_scaling
            y_offset = math.cos(culmination_ratio * 2 * math.pi) * (90 - self.sources[i][2]) * self.degree_scaling

            marker_rect = self.source_items[i][1].rect()
            self.source_items[i][1].setRect(x_offset - marker_rect.width() / 2,
                                            -(90 - self.coordinates[0]) * self.degree_scaling + y_offset
                                            - marker_rect.height() / 2,
                                            marker_rect.width(), marker_rect.height())

            marker_rect_new = self.source_items[i][1].rect()
            moved = (marker_rect_new.x() - marker_rect.x(), marker_rect_new.y() - marker_rect.y())
            self.source_items[i][2].moveBy(moved[0], moved[1])


def load_config(file=CONFIG_FILE):
    """Loads config file."""

    # Create config file if it doesn't exist yet
    if not os.path.isfile(CONFIG_FILE):
        shutil.copy("default_config.txt", CONFIG_FILE)
    
    with open(file, newline='', encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')
        next(csv_reader)  # Skip header row
        for row in csv_reader:
            print(f"Coordinates: {float(row[0]):.3f}° N, {float(row[1]):.3f}° E")
            return float(row[0]), float(row[1]), float(row[2]), float(row[3]), int(row[4]), int(row[5]), float(row[6])


def load_sources(file=SOURCE_FILE):
    """Load and return the source list."""

    # Create source file if it doesn't exist yet
    if not os.path.isfile(SOURCE_FILE):
        shutil.copy("default_sources.txt", SOURCE_FILE)

    types = []
    sources = []
    with open(file, newline='', encoding="utf-8") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter='|')
        next(csv_reader)  # Skip header row

        data_type = 0
        for row in csv_reader:
            if len(row) == 0:
                data_type += 1
                next(csv_reader)
                continue

            if data_type == 0:
                types.append((int(row[0]), row[1]))
            elif data_type == 1:
                right_ascension = row[1].split(':')
                right_ascension = int(right_ascension[0]) + int(right_ascension[1]) / 60. + float(right_ascension[2]
                                                                                                  ) / 3600

                declination = row[2].split(':')
                if declination[0][0] == '-':
                    sign = -1
                else:
                    sign = 1
                declination = sign * (int(declination[0][1:]) + int(declination[1]) / 60. + float(declination[2]) / 3600)

                sources.append([row[0], right_ascension, declination, int(row[3]), int(row[4])])

    return types, sources


def save_sources(types, sources, file=SOURCE_FILE):
    """Saves the source list with current options."""

    with open(file, 'w', newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter='|')
        csv_writer.writerow(["Source Size", "Source Color"])    # Write type header row
        for source_type in types:
            csv_writer.writerow(source_type)

        csv_writer.writerow([])
        csv_writer.writerow(["Source", "Right Ascension", "Declination", "Type", "Trace"])  # Write source header row
        for source in sources:
            right_ascension = f"{int(source[1]):02d}:{int((source[1] % 1) * 60):02d}" \
                              f":{((((source[1] % 1) * 60) % 1) * 60):06.3f}"

            if source[2] >= 0:
                declination = f"+{int(source[2]):02d}:{int((source[2] % 1) * 60):02d}" \
                              f":{((((source[2] % 1) * 60) % 1) * 60):06.3f}"
            else:
                declination = f"-{int(-source[2]):02d}:{int((-source[2] % 1) * 60):02d}" \
                              f":{((((-source[2] % 1) * 60) % 1) * 60):06.3f}"

            csv_writer.writerow((source[0], right_ascension, declination, source[3], source[4]))

    print("Sources saved!")
    return 0


def utc_to_lst(utc_time, coords):
    """Converts UTC time to LST."""

    time_since_vernal_equinox = (time.mktime(utc_time)
                                 - time.mktime(time.strptime(VERNAL_EQUINOX_UTC, "%Y-%m-%d %H:%M")))
    equinox_offset = 12 + time_since_vernal_equinox / (365 * 24 * 60 * 60) * 24
    longitude_offset = coords[1] / 360 * 24

    return time.gmtime(calendar.timegm(utc_time) + (equinox_offset + longitude_offset + LST_FIX) * 60 * 60)


def local_to_lst(local_time, coords):
    """Converts local civil time to LST."""

    utc_time = time.gmtime(local_time)
    return utc_to_lst(utc_time, coords)


def main():
    # Start with current time
    local_time = time.time()
    print("Local time:", time.strftime("%Y-%m-%d %H:%M", time.localtime(local_time)))
    print()

    # Handle GUI
    app = QApplication(sys.argv)
    view = GUIView(local_time)
    view.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
