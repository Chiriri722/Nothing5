# -*- coding: utf-8 -*-
"""
파일 내용 추출 모듈

PDF, DOCX, 이미지 등 다양한 파일 형식에서 텍스트와 메타데이터를 추출합니다.
"""

import logging
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
    from PIL.ExifTags import TAGS
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
        self.supported_extensions = {
            'pdf': ['.pdf'],
            'docx': ['.docx', '.doc'],
            'txt': ['.txt', '.md', '.log', '.py', '.js', '.json', '.xml', '.html', '.css', '.csv'],
            'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff']
        }

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
        
        try:
            content = ""
            metadata = {}

            # PDF
            if suffix in self.supported_extensions['pdf']:
                content = self.extract_text_from_pdf(file_path) or ""

            # DOCX
            elif suffix in self.supported_extensions['docx']:
                content = self.extract_text_from_docx(file_path) or ""

            # 이미지
            elif suffix in self.supported_extensions['image']:
                metadata = self.extract_metadata_from_image(file_path) or {}
                # 이미지는 텍스트 내용이 없으므로 메타데이터를 문자열로 변환하여 일부 제공 가능
                content = f"Image Metadata: {metadata}"

            # 텍스트 파일
            elif suffix in self.supported_extensions['txt']:
                content = self.extract_text_from_txt(file_path) or ""

            else:
                logger.debug(f"텍스트 추출 미지원 형식, 기본 처리: {suffix}")
                # 지원하지 않는 형식은 내용은 비워둠
                content = ""

            # 스마트 요약 (Smart Extraction)
            final_content = self._smart_truncate(content)

            return {
                "content": final_content,
                "metadata": metadata,
                "size": path.stat().st_size
            }

        except Exception as e:
            logger.error(f"파일 추출 중 오류 ({file_path}): {e}", exc_info=True)
            return {
                "content": "",
                "metadata": {},
                "error": str(e)
            }
    
    def _smart_truncate(self, text: str, limit: int = 1000) -> str:
        """
        텍스트 스마트 요약 (앞 1000자 + 뒤 1000자)
        """
        if not text:
            return ""

        if len(text) <= limit * 2:
            return text

        head = text[:limit]
        tail = text[-limit:]
        return f"{head}\n\n... [중간 내용 생략 ({len(text) - limit*2}자)] ...\n\n{tail}"

    def extract_text_from_pdf(self, file_path: str) -> Optional[str]:
        """PDF 파일에서 텍스트 추출"""
        if not PyPDF2:
            logger.warning("PyPDF2가 설치되지 않았습니다.")
            return None

        try:
            text_content = []
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                # 최대 10페이지까지만 읽어서 성능 최적화 (선택 사항, 여기서는 다 읽고 truncate에서 자름)
                # 또는 앞 2페이지, 뒤 2페이지만 읽을 수도 있음.
                # 여기서는 전체를 읽되, 너무 많으면 중단하는 식으로 구현 가능하지만,
                # 일단 전체 텍스트를 추출하고 _smart_truncate에 맡김.
                for page in reader.pages:
                    text_content.append(page.extract_text() or "")

            return "\n".join(text_content)
        except Exception as e:
            logger.error(f"PDF 추출 오류: {e}")
            return None
    
    def extract_text_from_docx(self, file_path: str) -> Optional[str]:
        """DOCX 파일에서 텍스트 추출"""
        if not docx:
            logger.warning("python-docx가 설치되지 않았습니다.")
            return None
            
        try:
            doc = docx.Document(file_path)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"DOCX 추출 오류: {e}")
            return None
    
    def extract_text_from_txt(self, file_path: str) -> Optional[str]:
        """일반 텍스트 파일 추출"""
        encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']
        
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"TXT 읽기 오류 ({enc}): {e}")
                return None

        logger.warning(f"텍스트 파일 인코딩 감지 실패: {file_path}")
        return None

    def extract_metadata_from_image(self, file_path: str) -> Optional[Dict[str, Any]]:
        """이미지 메타데이터 추출"""
        if not Image:
            logger.warning("Pillow가 설치되지 않았습니다.")
            return None

        try:
            with Image.open(file_path) as img:
                meta = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                    "width": img.width,
                    "height": img.height
                }
                # EXIF 데이터 처리 (필요시)
                return meta
        except Exception as e:
            logger.error(f"이미지 메타데이터 추출 오류: {e}")
            return None
