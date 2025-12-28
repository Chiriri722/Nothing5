# -*- coding: utf-8 -*-
"""
setup.py - 파일 분류 프로그램 설치 스크립트

LLM 기반 파일 자동 분류 프로그램을 패키지로 설치하기 위한 설정 파일입니다.
"""

from setuptools import setup, find_packages
from pathlib import Path

# README 파일 읽기
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8") if (this_directory / "README.md").exists() else ""

setup(
    name="file-classifier",
    version="1.0.0",
    description="LLM 기반 파일 자동 분류 프로그램",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI File Classifier Team",
    author_email="contact@example.com",
    url="https://github.com/example/file-classifier",
    license="MIT",
    
    # 프로젝트 분류
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: X11 Applications :: Tkinter",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Korean",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Utilities",
        "Topic :: System :: Filesystems",
    ],
    
    # 패키지 설정
    packages=find_packages(),
    include_package_data=True,
    
    # Python 버전 요구사항
    python_requires=">=3.8",
    
    # 의존성
    install_requires=[
        "openai>=0.27.0",           # OpenAI API
        "python-dotenv>=0.21.0",    # 환경 변수 로드
        "watchdog>=3.0.0",          # 파일 감시
        "pathlib2>=2.3.7.post1",   # 경로 처리 (Python 3.8 호환성)
    ],
    
    # 개발 의존성
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "isort>=5.10.0",
        ],
    },
    
    # 콘솔 스크립트 진입점
    entry_points={
        "console_scripts": [
            "file-classifier=file_classifier.main:main",
        ],
        "gui_scripts": [
            "file-classifier-gui=file_classifier.main:main",
        ],
    },
    
    # 프로젝트 메타데이터
    project_urls={
        "Bug Reports": "https://github.com/example/file-classifier/issues",
        "Source": "https://github.com/example/file-classifier",
        "Documentation": "https://github.com/example/file-classifier/wiki",
    },
    
    # 키워드
    keywords="file classification llm ai automatic organization",
    
    # ZIP 안전 설정
    zip_safe=False,
)
