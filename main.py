import streamlit as st
import pandas as pd
import numpy as np
import boto3
from audiorecorder import audiorecorder
from datetime import datetime
import io

st.title('mdc Clinical Notes')

s3 = boto3.Session(aws_access_key_id=st.secrets['aws_access_key'], 
                    aws_secret_access_key=st.secrets['aws_secret_access_key'])
cli = s3.client('s3')

audio = audiorecorder("Click to record", "Click to stop recording")

if st.button('Upload recording') and len(audio) > 0:
    filename = str(datetime.now())
    url = f's3://mdc-transcribe/{filename}.mp3'
    buffer = io.BytesIO()
    audio.export(buffer, format="wav")
    cli.put_object(
    Bucket='mdc-transcribe',
    Key=f'{filename}.wav',
    Body=buffer)
    st.write("Done!")
    audio = None
# s3.meta.client.upload_file('filename', 'mdc-transcribe', 'desired filename in s3')