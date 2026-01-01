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

        Args:
            file_path (str): 텍스트 파일 경로

        Returns:
            Dict[str, Any]: 추출 결과
        """
        try:
            # 인코딩 감지 시도 (단순히 utf-8 시도 후 cp949 시도)
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']
            content = ""
            encoding_used = ""

            for enc in encodings:
                try:
                    with open(file_path, 'r', encoding=enc) as f:
                        content = f.read()
                        encoding_used = enc
                        break
                except UnicodeDecodeError:
                    continue

            if not encoding_used:
                # 모든 인코딩 실패 시 ignore로 읽기
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    encoding_used = 'utf-8-ignore'

            full_len = len(content)

            # Smart Summary Logic
            if full_len <= 2000:
                extracted_text = content
            else:
                extracted_text = content[:1000] + "\n\n...[중간 생략]...\n\n" + content[-1000:]

            return {
                "content": extracted_text,
                "metadata": {"original_length": full_len},
                "encoding": encoding_used,
                "size": Path(file_path).stat().st_size
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

            # 본문 텍스트 추출
            for para in doc.paragraphs:
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

        logger.warning(f"텍스트 파일 인코딩 감지 실패: {file_path}")
        return None

if __name__ == "__main__":
    extractor = FileExtractor()
    print(f"지원 형식: {extractor.supported_extensions}")
