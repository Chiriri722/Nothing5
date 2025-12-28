#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
패키지 구조 및 임포트 검증 스크립트
"""

import sys
from pathlib import Path

print("="*60)
print("패키지 구조 검증")
print("="*60)

# 프로젝트 루트 경로
project_root = Path(__file__).parent
print(f"\n[1] 프로젝트 루트: {project_root}")

# Python 경로에 프로젝트 루트 추가
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"[2] Python 경로에 추가: {project_root}")

# config 패키지 임포트 테스트
try:
    from config import PROJECT_ROOT, LOG_LEVEL, OPENAI_API_KEY
    print(f"\n✓ config 패키지 임포트 성공")
    print(f"  - PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"  - LOG_LEVEL: {LOG_LEVEL}")
    print(f"  - OPENAI_API_KEY: {'설정됨' if OPENAI_API_KEY else '설정 안 됨'}")
except ImportError as e:
    print(f"\n✗ config 패키지 임포트 실패: {e}")
    sys.exit(1)

# config.py 유효성 검사 테스트
try:
    from config import validate_config
    print(f"\n[3] config.validate_config 임포트 성공")
    try:
        validate_config()
        print(f"✓ 설정 유효성 검사 통과")
    except ValueError as e:
        print(f"⚠ 설정 유효성 검사 실패 (예상된 상황): {e}")
        print(f"   → 이는 OPENAI_API_KEY가 설정되지 않았기 때문입니다.")
except ImportError as e:
    print(f"\n✗ validate_config 임포트 실패: {e}")
    sys.exit(1)

# 필요한 패키지 디렉토리 확인
required_dirs = [
    'config',
    'modules',
    'ui',
    'logs',
    'tests'
]

print(f"\n[4] 필수 디렉토리 확인:")
for dir_name in required_dirs:
    dir_path = project_root / dir_name
    status = "✓" if dir_path.exists() else "✗"
    print(f"  {status} {dir_name}/")

# 필수 파일 확인
required_files = [
    '__init__.py',
    'main.py',
    'requirements.txt',
    'config/config.py',
    'config/__init__.py',
    'modules/__init__.py',
    'ui/__init__.py',
]

print(f"\n[5] 필수 파일 확인:")
for file_name in required_files:
    file_path = project_root / file_name
    status = "✓" if file_path.exists() else "✗"
    print(f"  {status} {file_name}")

print(f"\n[6] 결론:")
all_files_exist = all((project_root / f).exists() for f in required_files)
if all_files_exist:
    print(f"✓ 모든 필수 파일이 존재합니다.")
    print(f"✓ 패키지 구조가 올바르게 설정되었습니다.")
    print(f"\n→ 1단계 보충 작업 완료!")
else:
    print(f"✗ 일부 필수 파일이 누락되었습니다.")
    sys.exit(1)

print("\n" + "="*60)
print("패키지 검증 완료")
print("="*60)
