from distutils.command.upload import upload
import streamlit as st
import pandas as pd
import numpy as np
import boto3
from audiorecorder import audiorecorder
from datetime import datetime
import io
from zoneinfo import ZoneInfo
import time
import json

st.title('mdc Clinical Notes')

s3 = boto3.Session(aws_access_key_id=st.secrets['aws_access_key'], 
                    aws_secret_access_key=st.secrets['aws_secret_access_key'])
cli = s3.client('s3')

tab1, tab2 = st.tabs(["Record & Scribe", "View Results"])

with tab1:
    st.subheader('Voice Record')
    col1, col2 = st.columns(2)
    with col1:
        audio = audiorecorder("Click to record", "Click to stop recording")
    with col2:
        upl = st.button('Upload recording')

    if upl and len(audio) > 0:
        
        filename = str(datetime.now().astimezone(ZoneInfo('Asia/Shanghai')).strftime("%Y-%m-%d_%H:%M:%S"))
        url = f's3://mdc-transcribe/{filename}.mp3'
        buffer = io.BytesIO()
        audio.export(buffer, format="wav")
        cli.put_object(
        Bucket='mdc-transcribe',
        Key=f'{filename}.wav',
        Body=buffer)
        st.subheader(":green[Done!]")
        audio = None

    st.divider()
    st.subheader("Scribe Recording")

    files = [x['Key'] for x in cli.list_objects_v2(Bucket='mdc-transcribe', MaxKeys=5)['Contents']]
    files.sort(reverse=True)

    select = st.selectbox("Choose the audio to scribe:", files)


    transcli = s3.client('transcribe')
    if st.button('Start Scribing'):
        job_name = str(select).replace(':', '.').replace(' ','_')
        try:
            response = transcli.start_medical_scribe_job(
                MedicalScribeJobName=job_name,
                Media={
                    'MediaFileUri': f's3://mdc-transcribe/{select}'
                },
                OutputBucketName='mdc-output',
                DataAccessRoleArn='arn:aws:iam::932424431774:role/transcriber',
                Settings={
                    'ShowSpeakerLabels': True,
                    'MaxSpeakerLabels': 2
                }
            )
        except:
            st.write("**This clip has already been scribed! Please scroll down to view it.**")
        
        else:
            while response['MedicalScribeJob']["MedicalScribeJobStatus"] != "COMPLETED":
                time.sleep(30)
                response = transcli.get_medical_scribe_job(MedicalScribeJobName=job_name)

            st.write(response)

with tab2:

    scribes = [x['Prefix'][:-1] for x in cli.list_objects_v2(Bucket='mdc-output', Delimiter="/", MaxKeys=11)['CommonPrefixes']]
    scribes.sort(reverse=True)
    summary = st.selectbox("Select a scribe to view",scribes)

    if st.button("View Scribe"):
        scr = cli.get_object(Bucket='mdc-output', Key=summary+'/summary.json')['Body'].read().decode('utf-8')
        json_content = json.loads(scr)
        sections = json_content['ClinicalDocumentation']['Sections']
        wanted = [0,2,5]
        for i in wanted:
            sect = sections[i]
            title = sect['SectionName'].replace("_", " ").lower()
            st.subheader(f':blue[{title}]')
            container = st.container(border=True)
            for summ in sect['Summary']:
                seg = summ['SummarizedSegment']
                container.write(seg)
            
