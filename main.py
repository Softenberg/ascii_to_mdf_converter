import cantools
from canlib import canlib, Frame
import time
import glob
import re
from asammdf import MDF, Signal
import streamlit as st
import os
from datetime import datetime, timedelta

def file_selector_input(folder_path='.'):
    filenames = os.listdir(folder_path+"/local_files/inputs/")
    selected_filename = st.selectbox('Select a ascii file', filenames)
    return os.path.join(folder_path, selected_filename), selected_filename

def file_selector(ch, folder_path='.'):
    filenames = os.listdir(os.path.join(folder_path, "local_files/dbc"))
    selected_filename = st.selectbox('Select a database for %s' % ch, filenames, key=f"db_selector_{ch}", index = 0)
    return os.path.join(folder_path, "local_files/dbc", selected_filename)

error_counter = 0
channels = []
db = []

channels_amount = st.number_input("How many channels to decode?", step=1, min_value=1, max_value=30, value=6)
temp, filename=file_selector_input()
file_path= "local_files/inputs/"+temp
data_list = []

with st.form("database_selection_form"):
    for i in range(channels_amount):
        channels.append(file_selector(f"channel {i+1}"))

    submit_button = st.form_submit_button("Submit")

# Do something with the selected databases after the form is submitted
if submit_button:
    for i in range(len(channels)):
        temp = (cantools.database.load_file(channels[i]))
        db.append(temp)

    

    pattern = re.compile(r'^date')
    date_format = "date %a %b %d %H:%M:%S %Y"
    pattern_ch = re.compile(r'\s*1\s*')
    pattern_id = re.compile(r'      1       (\w+)')
    pattern2 = re.compile(r'([\d.]+)\s+(\d+)\s+([0-9a-fA-F]+x)\s+(\w+)\s+(\w+)\s+(\d+)\s+([0-9a-fA-F ]+)')
    epoch = False
    
    progress=st.write("")
    # Open the file and read it line by line
    #print(db)
    with open(file_path, 'r') as file:
        for line in file:
            # Process each line as needed
            stripped_line=line.strip()  # Example: Print each line, removing leading and trailing whitespaces
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

    for index, i in enumerate(data_list):

        time_1 = i["time"]
                     
        for key, val in i.items():
            if type(val) == int or type(val) == float:
                try:
                    if epoch:
                        data_list2.append({'timestamp': int(start_date.timestamp() * 1_000_000)+int(round(float(time_1)*10000000)), 'signal_value': val, 'signal_name': key})
                    else:
                        data_list2.append({'timestamp': time_1, 'signal_value': val, 'signal_name': key})
                    progress = (index,"    ",len(data_list))
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
        mdf.append(signal)

    # Save MDF to a file

    string_start_date = string_start_date.replace(":", "-").replace(" ", "")
    mdf.save('local_files/outputs/Converted_ASCII_%s.dat' %(filename.replace(".asc", "")+string_start_date))
    print(error_counter)

