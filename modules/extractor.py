# -*- coding: utf-8 -*-
"""
파일 내용 추출 모듈

PDF, DOCX, 이미지 등 다양한 파일 형식에서 텍스트와 메타데이터를 추출합니다.
확장 가능한 핸들러 레지스트리 패턴을 사용하여 구조화되었습니다.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Set

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
    - TXT (텍스트 및 코드)
    - 이미지 (PNG, JPG, etc. - 메타데이터)

    새로운 파일 형식을 지원하려면 register_handler()를 사용하세요.
    """
    
    def __init__(self):
        """FileExtractor 초기화 및 기본 핸들러 등록"""
        self._handlers: Dict[str, Callable[[str], Dict[str, Any]]] = {}

        # 텍스트 파일 확장자 목록
        self.text_extensions: Set[str] = {
            '.txt', '.py', '.js', '.java', '.c', '.cpp', '.html', '.css', '.md', '.json', '.xml', '.yml', '.yaml'
        }

        # 이미지 파일 확장자 목록
        self.image_extensions: Set[str] = {
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp'
        }

        self._register_default_handlers()

    def _register_default_handlers(self):
        """기본 파일 핸들러 등록"""
        # 텍스트 핸들러 등록
        for ext in self.text_extensions:
            self.register_handler(ext, self.extract_text_from_txt)

        # 이미지 핸들러 등록
        for ext in self.image_extensions:
            self.register_handler(ext, self.extract_text_from_image)

        # 문서 핸들러 등록
        self.register_handler('.pdf', self.extract_text_from_pdf)
        self.register_handler('.docx', self.extract_text_from_docx)
        self.register_handler('.doc', self.extract_text_from_docx)

    def register_handler(self, extension: str, handler: Callable[[str], Dict[str, Any]]):
        """
        특정 확장자에 대한 핸들러를 등록합니다.

        Args:
            extension (str): 파일 확장자 (예: '.pdf')
            handler (Callable): 처리 함수
        """
        if not extension.startswith('.'):
            extension = '.' + extension
        self._handlers[extension.lower()] = handler

    @property
    def supported_extensions(self) -> list:
        """지원되는 모든 확장자 목록 반환"""
        return list(self._handlers.keys())

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
        handler = self._handlers.get(suffix)

        if not handler:
            logger.warning(f"지원하지 않는 파일 형식입니다: {suffix}")
            return None
        
        logger.info(f"파일 추출 시작: {file_path}")

        try:
            return handler(str(path))
        except Exception as e:
            logger.error(f"추출 중 오류 발생 ({file_path}): {e}")
            return None
    
    def extract_text_from_txt(self, file_path: str) -> Dict[str, Any]:
        """
        텍스트 파일에서 텍스트 추출 (Smart Summary: Front 1000 + Rear 1000)
        대용량 파일의 경우 전체를 읽지 않고 앞뒤 부분만 읽습니다.
        """
        try:
            file_size = Path(file_path).stat().st_size
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']

            content = ""
            encoding_used = ""

            # 작은 파일은 한번에 읽기 (2500바이트 이하)
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

            # 대용량 파일 처리
            front_text = ""
            rear_text = ""
            encoding_used = "utf-8" # 기본 가정

            with open(file_path, 'rb') as f:
                front_bytes = f.read(1500)
                f.seek(0, 2)
                file_end_pos = f.tell()
                seek_pos = max(0, file_end_pos - 1500)
                f.seek(seek_pos)
                rear_bytes = f.read()

            for enc in encodings:
                try:
                    test_bytes = front_bytes[:-4]
                    test_bytes.decode(enc)

                    front_text = front_bytes.decode(enc, errors='ignore')
                    rear_text = rear_bytes.decode(enc, errors='ignore')
                    encoding_used = enc
                    break
                except UnicodeDecodeError:
                    continue

            if not encoding_used:
                 front_text = front_bytes.decode('utf-8', errors='ignore')
                 rear_text = rear_bytes.decode('utf-8', errors='ignore')
                 encoding_used = 'utf-8-ignore'

            front_text = front_text[:1000]
            rear_text = rear_text[-1000:]

            extracted_text = front_text + "\n\n...[중간 생략]...\n\n" + rear_text

            return {
                "content": extracted_text,
                "metadata": {"original_length": file_size},
                "encoding": encoding_used,
                "size": file_size
            }

        except Exception as e:
            logger.error(f"텍스트 추출 오류: {e}")
            raise

    def extract_text_from_pdf(self, file_path: str) -> Optional[Dict[str, Any]]:
        """PDF 파일에서 텍스트 추출 (Smart Summary 적용)"""
        if not PyPDF2:
            logger.warning("PyPDF2가 설치되지 않았습니다.")
            return None

        try:
            text = ""
            page_count = 0

            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                page_count = len(reader.pages)

                if page_count <= 5:
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                else:
                    for i in range(2):
                        text += reader.pages[i].extract_text() + "\n"
                    text += "\n\n...[중간 페이지 생략]...\n\n"
                    for i in range(page_count - 2, page_count):
                        if i >= 2:
                             text += reader.pages[i].extract_text() + "\n"

            if len(text) > 2500:
                text = text[:1000] + "\n...[내용 생략]...\n" + text[-1000:]

            return {
                "content": text,
                "metadata": {"page_count": page_count},
                "size": Path(file_path).stat().st_size
            }

        except Exception as e:
            logger.error(f"PDF 추출 오류: {e}")
            raise
    
    def extract_text_from_docx(self, file_path: str) -> Optional[Dict[str, Any]]:
        """DOCX 파일에서 텍스트 추출 (Smart Summary 적용)"""
        if not docx:
            logger.warning("python-docx가 설치되지 않았습니다.")
            return None

        try:
            doc = docx.Document(file_path)
            paragraphs = doc.paragraphs
            total_paragraphs = len(paragraphs)
            full_text = []

            if total_paragraphs <= 100:
                for para in paragraphs:
                    full_text.append(para.text)
            else:
                for i in range(50):
                    full_text.append(paragraphs[i].text)
                full_text.append("\n...[중간 문단 생략]...\n")
                for i in range(total_paragraphs - 50, total_paragraphs):
                    full_text.append(paragraphs[i].text)

            text = '\n'.join(full_text)

            if len(text) > 2500:
                 text = text[:1000] + "\n...[내용 생략]...\n" + text[-1000:]

            return {
                "content": text,
                "metadata": {"paragraph_count": total_paragraphs},
                "size": Path(file_path).stat().st_size
            }

        except Exception as e:
            logger.error(f"DOCX 추출 오류: {e}")
            return None
    
    def extract_text_from_image(self, file_path: str) -> Optional[Dict[str, Any]]:
        """이미지 파일에서 메타데이터 추출"""
        if not Image:
            logger.warning("Pillow가 설치되지 않았습니다.")
            return None

        try:
            with Image.open(file_path) as img:
                width, height = img.size
                format_ = img.format
                mode = img.mode

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
