import openai
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def translate_rows_if_needed(df: pd.DataFrame) -> pd.DataFrame:
    """필요한 경우 기사를 번역합니다."""
    if not OPENAI_API_KEY:
        return df
    
    translated_df = df.copy()
    
    for idx, row in df.iterrows():
        # 영어로 된 기사인지 확인 (간단한 방법)
        title = str(row.get('title', ''))
        summary = str(row.get('summary', ''))
        
        if is_english_text(title + ' ' + summary):
            try:
                translated_title = translate_text(title)
                translated_summary = translate_text(summary) if summary else ''
                
                translated_df.at[idx, 'title'] = translated_title
                translated_df.at[idx, 'summary'] = translated_summary
                
            except Exception as e:
                print(f"번역 오류 (ID: {row.get('id', 'unknown')}): {e}")
                continue
    
    return translated_df

def is_english_text(text: str) -> bool:
    """텍스트가 영어인지 간단히 판단합니다."""
    if not text:
        return False
    
    english_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
    total_chars = sum(1 for c in text if c.isalpha())
    
    if total_chars == 0:
        return False
    
    return english_chars / total_chars > 0.7

def translate_text(text: str) -> str:
    """텍스트를 한국어로 번역합니다."""
    if not text or not OPENAI_API_KEY:
        return text
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 IT/기술 뉴스를 전문적으로 번역하는 번역가입니다. 자연스러운 한국어로 번역해주세요."},
                {"role": "user", "content": f"다음 영어 텍스트를 한국어로 번역해주세요:\n\n{text}"}
            ],
            max_tokens=300,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"번역 오류: {e}")
        return text