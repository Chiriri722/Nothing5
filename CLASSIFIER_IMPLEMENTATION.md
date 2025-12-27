# FileClassifier 모듈 구현 문서

## 개요

`classifier.py` 모듈은 OpenAI의 LLM(Language Model) API를 활용하여 파일의 내용을 분석하고 자동으로 적절한 폴더 이름을 추천하는 모듈입니다.

## 핵심 기능

### 1. FileClassifier 클래스

#### 초기화
```python
classifier = FileClassifier(api_key="your-api-key", model="gpt-3.5-turbo")
```

- **api_key**: OpenAI API 키 (환경변수 OPENAI_API_KEY에서도 자동 로드)
- **model**: 사용할 LLM 모델 (기본값: gpt-3.5-turbo)

#### 주요 메서드

##### `classify_file(filename, file_type, content)`
파일 내용을 기반으로 분류합니다.

**매개변수:**
- `filename` (str): 파일명
- `file_type` (str): 파일 확장자 (예: "pdf", "txt")
- `content` (str): 파일 내용

**반환값:**
```python
{
    "status": "success" | "error",
    "folder_name": "추천 폴더명",
    "category": "문서|이미지|비디오|음악|기타",
    "confidence": 0.85,  # 0.0 ~ 1.0
    "reason": "폴더명을 추천한 이유",
    "error": "에러메시지 (실패 시만)"
}
```

**사용 예시:**
```python
result = classifier.classify_file(
    "invoice.pdf",
    "pdf",
    "청구서 내용..."
)

if result["status"] == "success":
    print(f"폴더: {result['folder_name']}")
    print(f"신뢰도: {result['confidence']}")
else:
    print(f"오류: {result.get('error')}")
```

##### `classify_image(image_path)`
Vision API를 사용하여 이미지를 분류합니다.

**매개변수:**
- `image_path` (str): 이미지 파일의 절대 경로

**반환값:** `classify_file()`과 동일

**사용 예시:**
```python
result = classifier.classify_image("C:/path/to/photo.jpg")
print(result["folder_name"])  # "여행사진"
```

### 2. 파일 타입별 자동 분류

모듈은 다음 파일 타입을 인식합니다:

| 파일 타입 | 카테고리 |
|----------|----------|
| pdf, docx, doc, txt | 문서 |
| xlsx, xls | 스프레드시트 |
| csv | 데이터 |
| jpg, jpeg, png, gif, bmp, svg, webp | 이미지 |
| mp4, avi, mov, mkv, flv | 비디오 |
| mp3, wav, flac, aac, m4a | 음악 |

### 3. 에러 처리

모듈은 다음 에러 상황을 처리합니다:

- **API 키 오류**: 환경변수 확인 및 초기화 실패
- **레이트 제한 (429)**: 자동 폴백 분류
- **연결 오류**: 자동 폴백 분류
- **API 오류**: 상세 로깅 및 폴백 분류
- **응답 파싱 오류**: JSON 마크다운 블록 처리
- **타임아웃**: 설정된 시간 초과 시 폴백

모든 에러 상황에서 폴백 메커니즘이 작동하여 최소한의 분류 결과를 반환합니다.

## 설정

### 환경 변수

`.env` 파일에서 다음을 설정하세요:
```
OPENAI_API_KEY=sk-...
```

### config.py 연동

`config.py`에서 다음 값을 조정할 수 있습니다:

```python
LLM_MODEL = "gpt-3.5-turbo"  # 또는 "gpt-4"
LLM_TEMPERATURE = 0.7         # 0~2 범위
LLM_MAX_TOKENS = 500          # 최대 토큰 수
TIMEOUT = 30                  # API 호출 타임아웃 (초)
```

## 프롬프트 설계

### 텍스트 파일 프롬프트

모듈은 다음 정보를 LLM에 제공합니다:
- 파일명
- 파일 타입
- 콘텐츠 길이
- 파일 내용 (처음 1000자)

### 이미지 파일 프롬프트

Vision API를 사용하여 이미지를 Base64로 인코딩하여 전송합니다.

## 폴더명 검증

추천된 폴더명은 다음 기준으로 검증됩니다:

1. **금지된 문자 제거**: `\ / : * ? " < > |`
2. **길이 확인**: 2-30자 범위
3. **시스템 예약어 제외**: Documents, Desktop 등
4. **공백 정리**: 앞뒤 공백 제거

유효하지 않은 폴더명은 폴백 분류로 대체됩니다.

## 로깅

모듈은 표준 `logging` 모듈을 사용합니다:

```python
from logger import get_logger

logger = get_logger(__name__)
```

### 로그 메시지

- **INFO**: 분류 시작/완료, 성공적인 결과
- **DEBUG**: 프롬프트 생성, API 호출 정보
- **WARNING**: 폴더명 검증 실패, 폴백 사용
- **ERROR**: API 오류, 심각한 오류

## 테스트

### 테스트 실행

모든 테스트 실행:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

특정 테스트 파일 실행:
```bash
python -m unittest tests.test_classifier -v
```

특정 테스트 클래스 실행:
```bash
python -m unittest tests.test_classifier.TestValidateFolderName -v
```

특정 테스트 메서드 실행:
```bash
python -m unittest tests.test_classifier.TestValidateFolderName.test_valid_folder_name -v
```

### 테스트 커버리지

구현된 테스트 케이스:

#### 초기화 테스트
- API 키를 전달한 초기화
- API 키 없을 때 에러 발생
- 커스텀 모델 설정

#### 폴더명 검증 테스트
- 유효한 폴더명 검증
- 금지된 문자 제거
- 길이 범위 검사
- 시스템 예약어 필터링
- 빈 폴더명 처리

#### 폴백 분류 테스트
- 파일 타입 기반 분류
- 파일명 기반 분류
- 알 수 없는 타입 처리

#### 응답 파싱 테스트
- 유효한 JSON 파싱
- 마크다운 코드블록 처리
- 필드 누락 처리
- 잘못된 JSON 에러 처리

#### 파일 타입 테스트
- 이미지 파일 판별
- 비이미지 파일 판별
- 파일 타입별 카테고리 매핑

#### 에러 처리 테스트
- 에러 결과 생성
- 폴백 결과 생성

#### 프롬프트 템플릿 테스트
- 분류 프롬프트 구조 검증
- Vision 프롬프트 구조 검증

## 성능 최적화

### 콘텐츠 제한
- 파일 내용은 처음 1000자로 제한되어 API 호출 비용 최소화

### 타임아웃 설정
- 기본 타임아웃: 30초
- 응답이 없으면 폴백 분류 적용

### 동시 처리
- `MAX_WORKERS` 설정으로 동시 처리 수 제한

## 의존성

```
openai>=1.3.0           # OpenAI API
python-dotenv>=1.0.0    # 환경변수 로드
```

## 사용 예시

### 기본 사용
```python
from modules.classifier import FileClassifier

# 분류기 초기화
classifier = FileClassifier(api_key="sk-...")

# 파일 분류
result = classifier.classify_file(
    "document.pdf",
    "pdf",
    "이 문서는 2024년 분기별 재무 보고서입니다..."
)

print(f"추천 폴더: {result['folder_name']}")
print(f"카테고리: {result['category']}")
print(f"신뢰도: {result['confidence']:.2%}")
```

### 이미지 분류
```python
# 이미지 분류
result = classifier.classify_image("/path/to/vacation_photo.jpg")
print(result["folder_name"])  # "여행사진"
```

### 에러 처리
```python
result = classifier.classify_file(
    "file.txt",
    "txt",
    "Some content"
)

if result["status"] == "success":
    print(f"폴더: {result['folder_name']}")
else:
    print(f"에러: {result.get('error')}")
    # 폴백 폴더명도 제공됨
    print(f"폴백 폴더: {result['folder_name']}")
```

## 주요 특징

✅ **안정성**: 모든 오류 상황에 폴백 메커니즘
✅ **유연성**: 커스텀 모델 및 파라미터 설정 가능
✅ **확장성**: 새로운 파일 타입 추가 용이
✅ **투명성**: 상세한 로깅 및 신뢰도 점수
✅ **테스트**: 광범위한 단위 테스트 커버리지

## 제한사항

- API 키가 반드시 필요합니다
- 네트워크 연결이 필요합니다
- 대용량 파일은 처음 1000자만 분석합니다
- 이미지 분류는 `gpt-4-vision` 모델 권장

## 문제 해결

### "OPENAI_API_KEY가 설정되지 않았습니다" 에러

1. `.env` 파일에 `OPENAI_API_KEY=sk-...` 추가
2. 또는 코드에서 직접 전달: `FileClassifier(api_key="sk-...")`

### "API 레이트 제한 도달" 에러

1. 요청 빈도 감소
2. 또는 API 요금제 업그레이드

### 분류 결과가 부정확함

1. 파일 내용이 충분히 상세한지 확인
2. 모델을 `gpt-4`로 변경
3. `LLM_TEMPERATURE` 값 조정

## 라이선스

프로젝트 라이선스 정책 따름
