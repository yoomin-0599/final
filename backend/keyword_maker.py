import openai
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def extract_keywords(text: str) -> List[str]:
    """텍스트에서 키워드를 추출합니다."""
    if not text or not OPENAI_API_KEY:
        return []
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"""
        다음 텍스트에서 핵심 키워드를 추출해주세요. IT/기술 관련 키워드를 우선적으로 선택하고, 
        최대 8개까지 중요한 순서대로 나열해주세요. 각 키워드는 쉼표로 구분하여 반환해주세요.
        
        텍스트: {text[:1000]}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 IT/기술 뉴스의 키워드를 추출하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.3
        )
        
        keywords_text = response.choices[0].message.content.strip()
        keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
        
        return keywords[:8]
        
    except Exception as e:
        print(f"키워드 추출 오류: {e}")
        # 오류 시 기본 키워드 추출 로직 (간단한 방식)
        return extract_simple_keywords(text)

def extract_simple_keywords(text: str) -> List[str]:
    """간단한 키워드 추출 (백업 방식)"""
    keywords = []
    tech_terms = [
        'AI', '인공지능', '머신러닝', '딥러닝', '반도체', '5G', '6G',
        'IoT', '클라우드', '빅데이터', '블록체인', '메타버스', 'VR', 'AR',
        '로봇', '자동화', '스마트팩토리', '디지털전환', 'DX', '핀테크',
        '전기차', '자율주행', '배터리', '태양광', '풍력', '수소',
        '양자컴퓨팅', '사이버보안', '해킹', '랜섬웨어', '개인정보보호',
        '스타트업', '유니콘', '벤처캐피탈', 'IPO', 'M&A'
    ]
    
    text_lower = text.lower()
    for term in tech_terms:
        if term.lower() in text_lower:
            keywords.append(term)
    
    return keywords[:8]