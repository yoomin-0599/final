#!pip install -q streamlit pandas openai pyvis pyngrok

#----여기부터 실행----
from google.colab import drive
drive.mount('/content/drive')

import sys
# main_app.py가 있는 폴더 경로
main_app_folder ="/content/drive/MyDrive/Colab Projects/keyword_network_project"

%cd {main_app_folder}

import os
from google.colab import userdata
from pyngrok import ngrok
import time

os.environ['OPENAI_API_KEY'] = userdata.get('proper')

authtoken = userdata.get('NGROK_AUTHTOKEN')

ngrok.set_auth_token(authtoken)

public_url = ngrok.connect(8501)
print(f"🌍 Streamlit 앱 접속 주소: {public_url}")

!streamlit run main_app.py