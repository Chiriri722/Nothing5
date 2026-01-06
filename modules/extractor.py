# -*- coding: utf-8 -*-
"""
파일 내용 추출 모듈

PDF, DOCX, 이미지 등 다양한 파일 형식에서 텍스트와 메타데이터를 추출합니다.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)


class FileExtractor:
    """
    파일에서 내용을 추출하는 클래스
    
    지원 형식:
    - PDF
    - DOCX (Word 문서)
    - TXT (텍스트)
    - 이미지 (PNG, JPG, etc. - 메타데이터)
    """
    
    def __init__(self):
        """FileExtractor 초기화"""
        self.supported_extensions = [
            '.pdf', '.docx', '.doc', '.txt', 
            '.py', '.js', '.java', '.c', '.cpp', '.html', '.css', '.md', '.json', '.xml', '.yml', '.yaml',
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp'
        ]

        # 텍스트 파일 확장자 목록
        self.text_extensions = {
            '.txt', '.py', '.js', '.java', '.c', '.cpp', '.html', '.css', '.md', '.json', '.xml', '.yml', '.yaml'
        }

        # 이미지 파일 확장자 목록
        self.image_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp'
        }

    async def extract_async(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        비동기적으로 파일 내용을 추출합니다.
        블로킹 작업을 스레드 풀에서 실행합니다.
        """
        return await asyncio.to_thread(self.extract, file_path)
    
    def extract(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        파일에서 내용 추출
        
        Args:
            file_path (str): 추출할 파일 경로
            
        Returns:
            Dict[str, Any]: 추출된 내용과 메타데이터
                - content: 추출된 텍스트 (스마트 요약 적용)
                - metadata: 메타데이터
                - size: 파일 크기
        """
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"파일을 찾을 수 없습니다: {file_path}")
            return None
        
        suffix = path.suffix.lower()
        if suffix not in self.supported_extensions:
            logger.warning(f"지원하지 않는 파일 형식입니다: {suffix}")
            return None
        
        logger.info(f"파일 추출 시작: {file_path}")

        try:
            if suffix in self.text_extensions:
                return self.extract_text_from_txt(str(path))
            elif suffix == '.pdf':
                return self.extract_text_from_pdf(str(path))
            elif suffix in ['.docx', '.doc']:
                return self.extract_text_from_docx(str(path))
            elif suffix in self.image_extensions:
                return self.extract_text_from_image(str(path))
        except Exception as e:
            logger.error(f"추출 중 오류 발생 ({file_path}): {e}")
            return None

        return None
    
    def extract_text_from_txt(self, file_path: str) -> Dict[str, Any]:
        """
        텍스트 파일에서 텍스트 추출 (Smart Summary: Front 1000 + Rear 1000)
        대용량 파일의 경우 전체를 읽지 않고 앞뒤 부분만 읽습니다.

        Args:
            file_path (str): 텍스트 파일 경로

        Returns:
            Dict[str, Any]: 추출 결과
        """
        try:
            file_size = Path(file_path).stat().st_size
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']

            content = ""
            encoding_used = ""

            # 작은 파일은 한번에 읽기 (최적화: 파일을 한번만 읽고 메모리에서 디코딩 시도)
            if file_size <= 2500:
                raw_data = b""
                with open(file_path, 'rb') as f:
                    raw_data = f.read()

                for enc in encodings:
                    try:
                        content = raw_data.decode(enc)
                        encoding_used = enc
                        break
                    except UnicodeDecodeError:
                        continue

                if not encoding_used:
                    content = raw_data.decode('utf-8', errors='ignore')
                    encoding_used = 'utf-8-ignore'

                return {
                    "content": content,
                    "metadata": {"original_length": len(content)},
                    "encoding": encoding_used,
                    "size": file_size
                }

            # 대용량 파일은 앞뒤 1000자만 읽기
            # Seek을 사용하기 위해 바이트 모드로 열어서 디코딩

            front_text = ""
            rear_text = ""
            encoding_used = "utf-8" # 기본 가정

            # 앞부분 읽기
            with open(file_path, 'rb') as f:
                # 넉넉하게 읽어서 디코딩 (멀티바이트 문자 고려)
                front_bytes = f.read(1500)

                # 뒷부분 읽기
                f.seek(0, 2) # 끝으로 이동
                file_end_pos = f.tell()
                seek_pos = max(0, file_end_pos - 1500)
                f.seek(seek_pos)
                rear_bytes = f.read()

            # 디코딩 시도
            for enc in encodings:
                try:
                    # 인코딩 감지를 위해 엄격한 모드로 시도 (중간 잘림 방지를 위해 약간 줄여서 테스트)
                    # 앞부분의 대부분이 정상적으로 디코딩된다면 해당 인코딩일 확률이 높음
                    test_bytes = front_bytes[:-4] # 멀티바이트 문자 최대 길이만큼 제외하고 테스트
                    test_bytes.decode(enc) # 실패시 UnicodeDecodeError 발생

                    # 인코딩이 확인되면, 실제 변환은 errors='ignore'로 수행 (바운더리 잘림 처리)
                    front_text = front_bytes.decode(enc, errors='ignore')
                    rear_text = rear_bytes.decode(enc, errors='ignore')
                    encoding_used = enc
                    break
                except UnicodeDecodeError:
                    continue

            # 모든 인코딩 실패시 (여기까지 올 일은 거의 없지만)
            if not encoding_used:
                 front_text = front_bytes.decode('utf-8', errors='ignore')
                 rear_text = rear_bytes.decode('utf-8', errors='ignore')
                 encoding_used = 'utf-8-ignore'

            # 길이 맞추기
            front_text = front_text[:1000]
            rear_text = rear_text[-1000:]

            extracted_text = front_text + "\n\n...[중간 생략]...\n\n" + rear_text

            return {
                "content": extracted_text,
                "metadata": {"original_length": file_size}, # 근사치
                "encoding": encoding_used,
                "size": file_size
            }

        except Exception as e:
            logger.error(f"텍스트 추출 오류: {e}")
            raise

    def extract_text_from_pdf(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        PDF 파일에서 텍스트 추출
        
        Args:
            file_path (str): PDF 파일 경로
            
        Returns:
            Optional[Dict[str, Any]]: 추출 결과
        """
        if not PyPDF2:
            logger.warning("PyPDF2가 설치되지 않았습니다.")
            return None

        try:
            text = ""
            page_count = 0

            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                page_count = len(reader.pages)

                # 최대 5페이지까지만 읽기 (성능 최적화)
                max_pages = min(5, page_count)

                for i in range(max_pages):
                    page = reader.pages[i]
                    text += page.extract_text() + "\n"

            # 텍스트 길이 제한
            if len(text) > 2000:
                text = text[:1000] + "\n...[생략]...\n" + text[-1000:]

            return {
                "content": text,
                "metadata": {"page_count": page_count},
                "size": Path(file_path).stat().st_size
            }

        except Exception as e:
            logger.error(f"PDF 추출 오류: {e}")
            raise
    
    def extract_text_from_docx(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        DOCX 파일에서 텍스트 추출
        
        Args:
            file_path (str): DOCX 파일 경로
            
        Returns:
            Optional[Dict[str, Any]]: 추출 결과
        """
        if not docx:
            logger.warning("python-docx가 설치되지 않았습니다.")
            return None

        try:
            doc = docx.Document(file_path)
            full_text = []

            # 본문 텍스트 추출 (최대 100문단까지만 읽어서 최적화)
            for i, para in enumerate(doc.paragraphs):
                if i >= 100: break
                full_text.append(para.text)

            text = '\n'.join(full_text)

            # 텍스트 길이 제한
            if len(text) > 2000:
                text = text[:1000] + "\n...[생략]...\n" + text[-1000:]

            return {
                "content": text,
                "metadata": {"paragraph_count": len(doc.paragraphs)},
                "size": Path(file_path).stat().st_size
            }

        except Exception as e:
            logger.error(f"DOCX 추출 오류: {e}")
            return None # DOCX 오류는 무시하고 None 반환 (분류 시 fallback 사용)
    
    def extract_text_from_image(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        이미지 파일에서 메타데이터 추출
        
        Args:
            file_path (str): 이미지 파일 경로
            
        Returns:
            Optional[Dict[str, Any]]: 추출 결과
        """
        if not Image:
            logger.warning("Pillow가 설치되지 않았습니다.")
            return None

        try:
            with Image.open(file_path) as img:
                width, height = img.size
                format_ = img.format
                mode = img.mode

                # 메타데이터를 텍스트로 변환하여 LLM에 제공
                content = f"이미지 정보:\n형식: {format_}\n크기: {width}x{height}\n모드: {mode}"

                return {
                    "content": content,
                    "metadata": {
                        "width": width,
                        "height": height,
                        "format": format_,
                        "mode": mode
                    },
                    "size": Path(file_path).stat().st_size
                }

        except Exception as e:
            logger.error(f"이미지 추출 오류: {e}")
            return None

if __name__ == "__main__":
    extractor = FileExtractor()
    print(f"지원 형식: {extractor.supported_extensions}")
