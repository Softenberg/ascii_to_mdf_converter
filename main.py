import cantools
from canlib import canlib, Frame
import time
import glob
import re
from asammdf import MDF, Signal
import streamlit as st
import os
from datetime import datetime, timedelta

def file_selector(ch, folder_path='.'):
    filenames = os.listdir(folder_path+"/local_files/dbc")
    selected_filename = st.selectbox('Select a database for %s' % ch, filenames)
    return os.path.join(folder_path, selected_filename)

def file_selector_input(folder_path='.'):
    filenames = os.listdir(folder_path+"/local_files/inputs/")
    selected_filename = st.selectbox('Select a ascii file', filenames)
    return os.path.join(folder_path, selected_filename), selected_filename


ch1 = file_selector("channel 1")
ch2 = file_selector("channel 2")
ch3 = file_selector("channel 3")
ch4 = file_selector("channel 4")
ch5 = file_selector("channel 5")
ch6 = file_selector("channel 6")

error_counter = 0

db1 = cantools.database.load_file("local_files/dbc/"+ch1)
db2 = cantools.database.load_file("local_files/dbc/"+ch2)
db3 = cantools.database.load_file("local_files/dbc/"+ch3)
db4 = cantools.database.load_file("local_files/dbc/"+ch4)
db5 = cantools.database.load_file("local_files/dbc/"+ch5)
db6 = cantools.database.load_file("local_files/dbc/"+ch6)

db= [db1, db2, db3, db4, db5, db6]

pattern = re.compile(r'^date')
date_format = "date %a %b %d %H:%M:%S %Y"
pattern_ch = re.compile(r'\s*1\s*')
pattern_id = re.compile(r'      1       (\w+)')
pattern2 = re.compile(r'([\d.]+)\s+(\d+)\s+([0-9a-fA-F]+x)\s+(\w+)\s+(\w+)\s+(\d+)\s+([0-9a-fA-F ]+)')


temp, filename=file_selector_input()
file_path= "local_files/inputs/"+temp
data_list = []

# Open the file and read it line by line
if st.button('Generate mdf3 file'):
    with open(file_path, 'r') as file:
        for line in file:
            # Process each line as needed
            stripped_line=line.strip()  # Example: Print each line, removing leading and trailing whitespaces
            if pattern.match(stripped_line):
                start_date = datetime.strptime(stripped_line, date_format)

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
                    dat = db[int(channel)-1].decode_message(message_id, hex_integers)
                except Exception as e:
                    #print(error_counter)
                    #print(e)
                    error_counter +=1
                    continue
                dat_2 = {}
                for i in dat:
                    nam = "channel"+channel+"_"+i+"_"+str(message_id)
                    dat_2[nam] = dat[i]
                dat = dat_2
                #print(dat)
                dat["time"] = timestamp
                data_list.append(dat)
                    
    data_list2 = []

    for i in data_list:

        time_1 = i["time"]
                     
        for key, val in i.items():
            if type(val) == int or type(val) == float:
                try:
                    data_list2.append({'timestamp': start_date+timedelta(microseconds=int(round(float(time_1)*1000000))), 'signal_value': val, 'signal_name': key})
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
        signal = Signal(samples=signal_data['values'], timestamps=signal_data['timestamps'], name=signal_name, unit='')
        # Append the Signal object to the MDF
        mdf.append(signal, timestamp=True)

    # Save MDF to a file

    mdf.save('local_files/outputs/Converted_ASCII_%s.dat' %filename)

