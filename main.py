import cantools
from canlib import canlib, Frame
import time
import glob
import re
from asammdf import MDF, Signal

db1 = cantools.database.load_file("local_files/EP1.dbc")


message_id = 0xcff78f3
data = [0xE9, 0x7F, 0xE4, 0x7F, 0xEF, 0x7F, 0x5D, 0xF9]
pattern = re.compile(r'^Begin TriggerBlock')
pattern_ch = re.compile(r'\s*1\s*')
pattern_id = re.compile(r'      1       (\w+)')
pattern2 = re.compile(r'([\d.]+)\s+(\d+)\s+([0-9a-fA-F]+x)\s+(\w+)\s+(\w+)\s+(\d+)\s+([0-9a-fA-F ]+)')



decoded_message = db1.decode_message(message_id, data)

# Print the decoded message
#print(decoded_message)

# Specify the path to your text file
file_path = 'local_files/wakawaka.asc'
data_list = []

# Open the file and read it line by line
with open(file_path, 'r') as file:
    for line in file:
        # Process each line as needed
        stripped_line=line.strip()  # Example: Print each line, removing leading and trailing whitespaces
        if pattern.match(stripped_line):
            start_date = stripped_line

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
            message_id=int(message_id, 16)
 
            hex_values = data.split()
            hex_integers = [int(value, 16) for value in hex_values]
            
            try:
                dat = db1.decode_message(message_id, hex_integers)
                dat["time"] = timestamp
                data_list.append(dat)
            except Exception as e:
                print(e)
                continue
                

data_list2 = []

for i in data_list:
    time_1 = i["time"]
    for key, val in i.items():
        if type(val) == int or type(val) == float:
            data_list2.append({'timestamp': time_1, 'signal_value': val, 'signal_name': key})


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
    signal = Signal(samples=signal_data['values'], timestamps=signal_data['timestamps'], name=signal_name, unit='')
    # Append the Signal object to the MDF
    mdf.append(signal)

# Save MDF to a file
start_date=start_date.replace("Begin TriggerBlock ", "_")
start_date=start_date.replace(" ", "_")
start_date=start_date.replace(":", "-")
mdf.save('local_files/output%s.dat' % start_date)
