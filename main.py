import streamlit as st
import pandas as pd
import numpy as np
import boto3
from st_audiorec import st_audiorec

st.title('mdc Clinical Notes')

wav_audio_data = st_audiorec()

if wav_audio_data is not None:
    st.audio(wav_audio_data, format='audio/wav')

s3 = boto3.resource('s3', aws_access_key_id=st.secrets['aws_access_key'], 
                    aws_secret_access_key=st.secrets['aws_secret_access_key'])

# s3.meta.client.upload_file('filename', 'mdc-transcribe', 'desired filename in s3')