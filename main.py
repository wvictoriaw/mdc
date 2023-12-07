import streamlit as st
import pandas as pd
import numpy as np
import boto3

st.title('mdc Clinical Notes')

s3 = boto3.resource('s3')

for bucket in s3.buckets.all():
    st.write(bucket.name)