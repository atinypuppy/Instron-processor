import streamlit as st
import pandas as pd
import glob
import numpy as np
import scipy
import math
import re
import tkinter as tk
from tkinter import filedialog
import calc

st.set_page_config(layout="wide")
#"st.session_state object:",st.session_state

####################################################################################
@st.cache_data(show_spinner=False)
def makeDF(folder):
    files = glob.glob(fr'{folder}\\**\*tracking.csv',recursive=True)
    cols = ['filename','TR Number','TR Sample Name','Form','Leave this Blank',
            'Sample Name','PSI','Size','Left/Right','Tup','Location',
            'Heel height','FF height']
    params = pd.DataFrame(columns=cols)
    try:
        trNumber = int(re.findall(r"TR\d{4}",folder)[0][2:])
    except:
        print('No TR number found')
        trNumber = None
    for f in files:
        x =re.findall(r'[^\\]+(?=\.)',f)[0]
        trName = re.split('\.',x)[0]
        arr = re.split('-',x)
        loc= []
        LR = []
        for i in arr:
            if i.lower().find('forefoot') != -1:
                loc.append('forefoot')
            elif i.lower().find('heel') != -1:
                loc.append('heel')
            if i.lower().find('left') != -1:
                LR.append('left')
            elif i.lower().find('right') != -1:
                LR.append('right')

        try:
            LR = LR[0].upper()
        except:
            LR = 'No L/R found'.upper()       
        try:
            loc = loc[0].upper()
        except:
            loc = 'No location found'.upper()
        sampleName = trName.replace(f'-{loc}','').replace(f'-{LR}','')
        
        temp = pd.DataFrame([[x,trNumber,trName,None,None,
                              sampleName,None,None,LR,None,loc,
                              None,None]],columns=cols)
        params = pd.concat([params,temp])
    return params
####################################################################################        

def run():
    status = st.write("Data Processing...")
    st.session_state['edit_params'] = edit_data    
    calc.processFolder(st.session_state.folder,st.session_state.savename,edit_data)
    status = st.write("DONE!")
    
####################################################################################
if 'folder' not in st.session_state:
    st.session_state.folder = None
if "params" not in st.session_state:
    st.session_state['params'] = pd.DataFrame()
    st.session_state.ready = False
if "df_ready" not in st.session_state:
    st.session_state['df_ready'] = 0


process = None
# Set up tkinter
root = tk.Tk()
root.withdraw()
# Make folder picker dialog appear on top of other windows
root.wm_attributes('-topmost', 1)
with st.form('file_picker'):
# Folder picker button
    st.title('Folder Picker')
    st.write('Please select a folder:')
    clicked = st.form_submit_button('Folder Picker')
    if clicked:
        st.session_state.folder = st.text_input('Selected folder:', filedialog.askdirectory(master=root))
        df = makeDF(st.session_state.folder)
        st.session_state['params'] = df
        st.session_state['df_ready'] = 1


if not st.session_state['params'].empty:
    st.write(f'FOLDER SELECTED: {st.session_state.folder}')
    edit_data = st.data_editor(st.session_state['params'])
    st.session_state.ready = st.checkbox('Parameters Entered')
    savename = st.text_input('Name the output file name','TR summary')
    st.session_state.savename = f'{savename}.csv'
    process = st.button('Process Data',key='process',disabled=not(st.session_state.ready))

if process:
    run()
