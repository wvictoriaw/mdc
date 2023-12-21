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
# from fpdf import FPDF

if "audio" not in st.session_state:
    st.session_state.audio = ""

st.title('mNote', anchor=False)

s3 = boto3.Session(aws_access_key_id=st.secrets['aws_access_key'], 
                    aws_secret_access_key=st.secrets['aws_secret_access_key'],
                    region_name = 'us-east-1')
cli = s3.client('s3')

tab1, tab2 = st.tabs(["Record & Scribe", "View Results"])

with tab1:
    st.subheader('Voice Record', anchor=False)

    audio = audiorecorder("Click to record", "Click to stop recording")
    aud = len(audio) > 0
    wrapper = st.empty()
    with wrapper.container():
        if aud:
            con = st.empty()
            with con.container():
                st.success('Recording is ready for upload! :tada:')

            upl = False
            uplcon = st.empty()
            with uplcon.container():
                upl = st.button('Upload recording', type='primary')
            recagain = st.empty()
            with recagain.container(): 
                if st.button("Record again"):
                    wrapper.empty()


            if upl and len(audio) > 0:
                recagain.empty()
                con.empty()
                with con.container():
                    st.info('Upload in progress...')
                filename = str(datetime.now().astimezone(ZoneInfo('Asia/Shanghai')).strftime("%Y-%m-%d_%H:%M:%S"))
                url = f's3://mdc-transcribe/{filename}.mp3'
                buffer = io.BytesIO()
                audio.export(buffer, format="wav")
                cli.put_object(
                Bucket='mdc-transcribe',
                Key=f'{filename}.wav',
                Body=buffer)
                with con.container():
                    st.success("Upload done! :tada:")
                uplcon.empty()
            with recagain.container(): 
                if st.button("Start a new transcript"):
                    wrapper.empty()
                

    st.divider()
    st.subheader("Scribe Recording", anchor=False)

    files = [x['Key'] for x in cli.list_objects_v2(Bucket='mdc-transcribe')['Contents']]
    files.sort(reverse=True)
    files = files[:5]

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
            st.write("**This clip has already been scribed! You may download it in the View Results tab.**")
        
        else:
            while response['MedicalScribeJob']["MedicalScribeJobStatus"] != "COMPLETED":
                time.sleep(30)
                response = transcli.get_medical_scribe_job(MedicalScribeJobName=job_name)

            st.success("Scribe complete! :tada:")

with tab2:

    scribes = [x['Prefix'][:-1] for x in cli.list_objects_v2(Bucket='mdc-output', Delimiter="/")['CommonPrefixes']]
    scribes.sort(reverse=True)
    scribes = scribes[:5]
    summary = st.selectbox("Select a scribe to view",scribes)

    typ = st.radio("scribe type", ["Patient's View", "Doctor's View"], label_visibility='collapsed', horizontal=True)

    if st.button("View Scribe", type='primary'):
        scr = cli.get_object(Bucket='mdc-output', Key=summary+'/summary.json')['Body'].read().decode('utf-8')
        json_content = json.loads(scr)
        sections = json_content['ClinicalDocumentation']['Sections']

        wanted = [0,2,5] if typ == "Patient's View" else [4]
        for i in wanted:
            sect = sections[i]
            title = sect['SectionName'].replace("_", " ").lower()
            st.subheader(f':blue[{title}]', anchor=False)
            container = st.container(border=True)
            for summ in sect['Summary']:
                seg = summ['SummarizedSegment']
                container.write(seg)
            