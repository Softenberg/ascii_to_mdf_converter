import sys
import os
import re
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QFormLayout, QSpinBox
from PyQt5.QtCore import Qt
import cantools
from asammdf import MDF, Signal

class MyMainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.file_path = None
        self.channels_amount = None
        self.channels = [None]*50
        self.db = []
        self.data_list = []
        self.error_counter = 0

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        file_button = QPushButton("select input file")
        self.file_path_label = QLabel()
        layout.addWidget(self.file_path_label)
        file_button.clicked.connect(self.select_file)
        layout.addWidget(file_button)

        channels_amount_layout = QFormLayout()
        self.channels_amount_input = QSpinBox()
        self.channels_amount_input.setRange(1, 30)
        self.channels_amount_input.setValue(6)
        self.channels_amount_input.valueChanged.connect(self.update_channel_buttons)  # Connect to the slot
        channels_amount_layout.addRow("Number of Channels:", self.channels_amount_input)
        layout.addLayout(channels_amount_layout)
        # Database Selector
        self.database_selector_layout = QVBoxLayout()  # Store layout as an instance variable
        self.db_selector_buttons = []




        for i in range(self.channels_amount_input.value()):  # Initialize buttons based on the default value
            db_selector_button = QPushButton(f"Select Database for Channel {i + 1}")
            db_selector_button.clicked.connect(lambda _, ch=i: self.select_database(ch))
            self.db_selector_buttons.append(db_selector_button)
            self.database_selector_layout.addWidget(db_selector_button)
        layout.addLayout(self.database_selector_layout)

        # Submit Button
        submit_button = QPushButton("Submit")
        submit_button.clicked.connect(self.process_data)
        layout.addWidget(submit_button)

        
        
        self.setLayout(layout)
        self.setWindowTitle("PyQt5 CAN Log Converter")

    def update_channel_buttons(self):
        new_channels_amount = self.channels_amount_input.value()

        while self.database_selector_layout.count() > 0:
            item = self.database_selector_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        self.db_selector_buttons = []
        for i in range(new_channels_amount):
            db_selector_button = QPushButton(f"Select Database for Channel {i + 1}")
            db_selector_button.clicked.connect(lambda _, ch=i: self.select_database(ch))
            self.db_selector_buttons.append(db_selector_button)
            self.database_selector_layout.addWidget(db_selector_button)

    def update_database_buttons_text(self):
        for i in range(self.channels_amount_input.value()):
            db_selector_button = self.db_selector_buttons[i]
            db_selector_button.setText(f"Select Database for Channel {i + 1}\n{self.channels[i].split('/')[-1] if self.channels[i] else 'No database selected'}")


    def select_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(self, "Select ASCII File", "", "ASCII Files (*.asc);;All Files (*)", options=options)
        if file_path:
            self.file_path = file_path
            self.file_path_label.setText(os.path.basename(file_path))

    def select_database(self, channel):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        db_path, _ = QFileDialog.getOpenFileName(self, f"Select Database for Channel {channel + 1}", "", "Database Files (*.dbc);;All Files (*)", options=options)
        if db_path:
            self.channels[channel] = db_path
            self.update_database_buttons_text()
            

    def process_data(self):
        self.channels_amount = self.channels_amount_input.value()

        for i in range(self.channels_amount):
            db_path = self.channels[i]
            if db_path:
                temp = cantools.database.load_file(db_path)
                self.db.append(temp)

        pattern = re.compile(r'^date')
        date_format = "date %a %b %d %H:%M:%S %Y"
        pattern2 = re.compile(r'([\d.]+)\s+(\d+)\s+([0-9a-fA-F]+x)\s+(\w+)\s+(\w+)\s+(\d+)\s+([0-9a-fA-F ]+)')
        epoch = False
        with open(self.file_path, 'r') as file:
            for line in file:
                stripped_line = line.strip()
                if pattern.match(stripped_line):
                    try:
                        start_date = datetime.strptime(stripped_line, date_format)
                    except:
                        start_date = "no date"
                    string_start_date = stripped_line

                match = pattern2.match(stripped_line)
                if match:
                    timestamp = match.group(1)
                    channel = match.group(2)
                    message_id = match.group(3)
                    direction = match.group(4)
                    data_type = match.group(5)
                    data_length = match.group(6)
                    data = match.group(7)
                    message_id = message_id.replace('x', '')
                    message_id = int(message_id, 16)

                    hex_values = data.split()
                    hex_integers = [int(value, 16) for value in hex_values]

                    try:
                        dat = self.db[int(channel) - 1].decode_message(message_id, hex_integers)
                    except Exception as e:
                        self.error_counter += 1
                        continue
                    dat_2 = {}
                    for i in dat:
                        nam = f"channel{channel}_{i}_{str(self.db[int(channel) - 1].get_message_by_frame_id(message_id).name)}"
                        dat_2[nam] = dat[i]
                    dat = dat_2
                    dat["time"] = timestamp
                    self.data_list.append(dat)

        # Rest of the processing logic...
        data_list2 = []

        for index, i in enumerate(self.data_list):

            time_1 = i["time"]
                        
            for key, val in i.items():
                if type(val) == int or type(val) == float:
                    try:
                        if epoch:
                            data_list2.append({'timestamp': int(start_date.timestamp() * 1_000_000)+int(round(float(time_1)*10000000)), 'signal_value': val, 'signal_name': key})
                        else:
                            data_list2.append({'timestamp': time_1, 'signal_value': val, 'signal_name': key})
                    except Exception as e:
                        print(e)
                        continue

        data_dict = {}
        for data_point in data_list2:
            signal_name = data_point['signal_name']
            if signal_name not in data_dict:
                data_dict[signal_name] = {'timestamps': [], 'values': []}
            data_dict[signal_name]['timestamps'].append(data_point['timestamp'])
            data_dict[signal_name]['values'].append(data_point['signal_value'])


        mdf = MDF(version='3.00')
        for signal_name, signal_data in data_dict.items():
            # Create Signal object for each signal
            #print(signal_name)
            signal = Signal(samples=signal_data['values'], timestamps=signal_data['timestamps'], name=signal_name, unit='')
            # Append the Signal object to the MDF
            mdf.append(signal)

        # Save MDF to a file

        string_start_date = string_start_date.replace(":", "-")
        mdf.save('Converted_ASCII_%s.dat' %(string_start_date))
        print(self.error_counter)
def main():
    app = QApplication(sys.argv)
    window = MyMainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
