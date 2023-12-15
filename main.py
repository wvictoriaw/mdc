import streamlit as st
import pandas as pd
import numpy as np
import boto3
from smart_open import open
from audiorecorder import audiorecorder
import datetime

st.title('mdc Clinical Notes')

s3 = boto3.Session(aws_access_key_id=st.secrets['aws_access_key'], 
                    aws_secret_access_key=st.secrets['aws_secret_access_key'])

audio = audiorecorder("Click to record", "Click to stop recording")

if st.button('Upload recording') and len(audio) > 0:
    filename = str(datetime.now())
    url = f's3://mdc-transcribe/{filename}.mp3'
    with open(url, 'wb', transport_params={'client': s3.client('s3')}) as fout:
        audio.export(fout, format='mp3')

# s3.meta.client.upload_file('filename', 'mdc-transcribe', 'desired filename in s3')