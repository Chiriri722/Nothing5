# -*- coding: utf-8 -*-
"""
프롬프트 템플릿 정의 모듈

LLM에 전송할 프롬프트를 관리합니다.
"""

CLASSIFICATION_PROMPT = """파일을 분석하여 적절한 폴더명을 추천해주세요.
정보: {filename}, {file_type}
내용:
{content}

규칙:
1. 한글로 된 의미있는 이름 (예: 청구서, 회의록)
2. 짧고 간결하게
3. 내용 기반 분류

JSON 응답:
{{
    "folder_name": "추천폴더명",
    "category": "문서|이미지|비디오|음악|기타",
    "confidence": 0.85,
    "reason": "이유"
}}"""

VISION_PROMPT = """이미지를 분석하여 폴더명을 추천해주세요.
정보: {filename}, {file_type}

규칙:
1. 한글로 된 의미있는 이름
2. 짧고 간결하게
3. 내용 기반

JSON 응답:
{{
    "folder_name": "추천폴더명",
    "category": "이미지",
    "confidence": 0.85,
    "reason": "이유"
}}"""
