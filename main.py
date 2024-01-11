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
import pdfkit
from streamlit_quill import st_quill


st.title('mNote', anchor=False)

s3 = boto3.Session(aws_access_key_id=st.secrets['aws_access_key'], 
                    aws_secret_access_key=st.secrets['aws_secret_access_key'],
                    region_name = 'us-east-1')
cli = s3.client('s3')

tab1, tab2, tab3 = st.tabs(["Record & Scribe", "View Summary", "Report Generator"])

with tab1:
    st.subheader('Record Consultation', anchor=False)

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
    st.subheader("Summarise a Recording", anchor=False)

    files = [x['Key'] for x in cli.list_objects_v2(Bucket='mdc-transcribe')['Contents']]
    files.sort(reverse=True)
    files = files[:5]

    select = st.selectbox("Choose the audio to summarise:", files)


    transcli = s3.client('transcribe')
    if st.button('Start Summarising', type='primary'):
        inf = st.empty()
        with inf.container():
            st.info('Summarising...')
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
            st.write("**This clip has already been summarised! You may download it in the View Summary tab.**")
        
        else:
            while response['MedicalScribeJob']["MedicalScribeJobStatus"] != "COMPLETED":
                time.sleep(15)
                response = transcli.get_medical_scribe_job(MedicalScribeJobName=job_name)
            
            inf.empty()
            with inf.container():
                st.success("Scribe complete! :tada:")

with tab2:
    
    scribes = [x['Prefix'][:-1] for x in cli.list_objects_v2(Bucket='mdc-output', Delimiter="/")['CommonPrefixes']]
    scribes.sort(reverse=True)
    scribes = scribes
    summary = st.selectbox("Select a summary to view",scribes)

    typ = st.radio("summary type", ["Doctor's View", "Patient's View"], label_visibility='collapsed', horizontal=True)

    dt = summary[:10]
    
    html = f'''<div style='width:100px;height:auto;position:absolute;right:0;top:-20px'><img src='https://static.tumblr.com/c1oapfr/8nTs6bnlb/logo_watermark.png' width='100%'></div>
    <h1 style='color:#005a97; font-family:sans-serif;margin:0;padding:0;'>Consultation Summary</h1>
<p style='color:#879198; font-family:sans-serif;font-size:12pt;margin:0;padding:2px;'><b>{typ}</b></p>
<p style='font-family:sans-serif;color:#999;font-size:11pt;'>Date of consultation: {dt}</p>'''

    if st.button("View Summary", type='primary'):
        load = st.empty()
        with load.container():
            st.info("Loading...")
        scr = cli.get_object(Bucket='mdc-output', Key=summary+'/summary.json')['Body'].read().decode('utf-8')
        json_content = json.loads(scr)
        sections = json_content['ClinicalDocumentation']['Sections']

        wanted = [0,2,5] if typ == "Patient's View" else [4]
        
        load.empty()
        for i in wanted:
            sect = sections[i]
            title = sect['SectionName'].replace("_", " ").title()
            html += f'''<br>
<h2 style='color:#005a97; font-family:sans-serif; font-size:18pt'>{title}</h2>
<div style='padding:10px 25px;border:1px solid #879198;border-radius:10px'>'''
            st.subheader(f':blue[{title}]', anchor=False)
            container = st.container(border=True)
            for summ in sect['Summary']:
                seg = summ['SummarizedSegment']
                container.write(seg.replace("$", "\$"))
                html += f'''<p style='font-family:sans-serif;line-height:25pt;'>{seg}</p>'''
            html += "</div>"

        pdf = pdfkit.from_string(html)
        pdf_stream = io.BytesIO()

        pdf_stream.write(pdf)

        st.download_button(
            label="Download Summary",
            data = pdf_stream,
            file_name = f'consult summary_{dt}_{typ}.pdf',
            mime = 'application/pdf',
            type = 'primary'
        )

    with tab3:
        st.header(":building_construction: UNDER CONSTRUCTION", anchor=False)
    #     scribes = [x['Prefix'][:-1] for x in cli.list_objects_v2(Bucket='mdc-output', Delimiter="/")['CommonPrefixes']]
    #     scribes.sort(reverse=True)
    #     scribes = scribes[:5]
    #     template = st.selectbox("Select a summary to start editing",scribes)

    #     dt = template[:10]
    #     sects = [0,2,4,5]
    
    #     header = f'''<div style='width:100px;height:auto;position:absolute;right:0;top:-20px'><img src='https://static.tumblr.com/c1oapfr/8nTs6bnlb/logo_watermark.png' width='100%'></div>
    #     <h1 style='color:#005a97; font-family:sans-serif;margin:0;padding:0;'>Consultation Summary</h1>
    # <p style='color:#879198; font-family:sans-serif;font-size:12pt;margin:0;padding:2px;'><b>Doctor's Report</b></p>
    # <p style='font-family:sans-serif;color:#999;font-size:11pt;'>Date of consultation: {dt}</p>'''
        
    #     if 'report' not in st.session_state:
    #         st.session_state.report = ""
        
    #     txt = ""
    #     dict = {}
    #     if st.button("Start Editing", type='primary'):
        
    #         scr = cli.get_object(Bucket='mdc-output', Key=summary+'/summary.json')['Body'].read().decode('utf-8')
    #         json_content = json.loads(scr)
    #         sections = json_content['ClinicalDocumentation']['Sections']
            
    #         for i in sects:
    #             sect = sections[i]
    #             title = sect['SectionName'].replace("_", " ").title()
    #             txt += f'''<br>
    # <h2 style='color:#005a97; font-family:sans-serif; font-size:18pt'>{title}</h2>
    # <div style='padding:10px 25px;border:1px solid #879198;border-radius:10px'>'''
    #             for summ in sect['Summary']:
    #                 seg = summ['SummarizedSegment']
    #                 txt += f'''<p style='font-family:sans-serif;line-height:25pt;'>{seg}</p>'''
    #             txt += "</div>"
    #             dict[title] = seg

    #         # pdf = pdfkit.from_string(html)
    #         # pdf_stream = io.BytesIO()

    #         # pdf_stream.write(pdf)

    #         # st.download_button(
    #         #     label="Download Summary",
    #         #     data = pdf_stream,
    #         #     file_name = f'consult summary_{dt}_{typ}.pdf',
    #         #     mime = 'application/pdf',
    #         #     type = 'primary'
    #         # )
    #         st.session_state.report= txt
        
    #     output = st_quill(value=st.session_state.report)
    #     st.text(output)