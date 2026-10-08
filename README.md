# 옵시디언 문서 변환기

Windows용 포터블 Markdown → DOCX/PPTX 변환 앱. Pandoc으로 변환하고, 문서 안의 한국어·영문·티베트어 텍스트를 구분하여 사용자 글꼴과 크기를 적용한다. Python이나 Microsoft Office를 설치하지 않아도 배포 EXE로 변환할 수 있다.

[최신 버전 다운로드](https://github.com/pong129/pandoc_obsidianmdtodocx/releases/latest)

## 실행

`dist/ObsidianToDocx.exe`를 실행한다. 같은 폴더의 `pandoc.exe`를 우선 사용하며, 시스템 설치본도 검색한다. Pandoc이 없으면 앱에서 포터블 설치/업데이트를 진행할 수 있다. 다운로드가 끝난 뒤 문서 변환은 오프라인으로 동작한다.

개발 실행:

```powershell
& '.venv\Scripts\python.exe' src/main.py
```

## 사용 흐름

왼쪽에서 파일·폴더 열기 또는 드래그 앤 드롭으로 Markdown을 가져온다. 오른쪽에서 DOCX/PPTX를 선택하고 언어별 글꼴·크기를 지정한다. 형식을 전환해도 파일 목록은 유지되고 각 형식의 마지막 설정은 별도로 기억한다. 이름을 붙인 서식 프리셋도 저장·삭제할 수 있다.

본문의 일반 크기와 한국어·티베트어 크기를 각각 지정한다. 제목과 각주의 언어별 크기는 해당 본문 크기의 비율로 계산한다. 예를 들어 일반 본문 12pt, 티베트어 20pt, 일반 제목 24pt이면 제목 속 티베트어는 40pt가 된다.

설정은 EXE 옆 `ObsidianConverter.ini`에 저장한다. 폴더에 쓰기 권한이 없으면 `%LOCALAPPDATA%/ObsiDeck`를 사용한다. 기존 버전의 레지스트리 설정은 최초 실행 때 읽어 옮긴다.

같은 이름의 결과 파일은 덮어쓰지 않고 `파일 (2).docx`처럼 번호를 붙인다. 후처리가 성공한 파일만 결과에 포함한다. DOCX → Markdown 보조 도구에서도 기존 Markdown 원문을 보존한다.

## 범위와 제한

- 기본 Markdown과 로컬 상대 경로 이미지를 처리한다. Obsidian 플러그인 전용 문법이나 노트 임베드/전개까지 재현하는 기능은 아니다.
- DOCX의 본문·제목·표·각주·머리말/꼬리말, PPTX 슬라이드의 제목·본문·표 텍스트에 언어별 서식을 적용한다. 차트·SmartArt·수식·필드·마스터 서식은 별도 범위다.
- 글꼴은 결과를 여는 컴퓨터에도 설치되어 있어야 한다. 실제 Office 렌더링 검증은 Microsoft Himalaya로 진행했다.
- PPTX 기본 슬라이드 분할은 제목 2(`##`) 기준이며 레이아웃 탭에서 변경할 수 있다. 상위 제목도 이어지는 본문과 함께 배치하며 연속된 제목은 같은 슬라이드에 둔다. 기본 본문 크기는 티베트어 20pt, 한국어 18pt다.
- PPTX의 본문 자동 분할은 기본으로 켜져 있다. 선택한 글꼴·크기를 Qt로 측정하고 여유 폭과 높이를 두어 다음 장으로 넘긴다. 같은 문단의 티베트어·한국어, 또는 티베트어 문단 바로 뒤의 한국어 번역 문단은 함께 넘긴다. 한 묶음 자체가 한 장보다 길면 축소하거나 번역을 따로 넘기지 않고, 해당 본문을 포함한 오류로 그 파일의 변환을 중단한다. 원문·번역 대응은 Markdown 문단 순서에 따르며 문장의 의미를 추론해 재배열하지 않는다.
- `***` 수동 구분은 유지한다. 자동으로 추가한 이어지는 슬라이드는 제목을 반복하지 않고 본문 영역을 넓힌다. 본문 자동 분할은 텍스트 상자 기준이며 표 행·그림·차트의 내용 분할은 지원하지 않는다. 글꼴이 다른 컴퓨터에서 대체되면 줄바꿈도 달라질 수 있다.
- 제목 없는 PPTX 슬라이드는 빈 제목 영역을 회수해 본문을 위쪽 0.25인치에서 시작한다. 본문 상자는 아래 여백까지 확장하되 아래쪽 표·그림과 겹치도록 늘리지 않는다. 제목이 있는 슬라이드의 배치는 유지한다.

## 개발과 검증

기존 PySide6와 python-docx 기반 구조 및 lxml을 사용한다. 새 서버·브라우저 엔진·AI 모델 의존성은 추가하지 않았다. python-pptx는 시험 문서 생성과 회귀 검사에도 사용한다. Word와 PowerPoint는 개발 중 시각 검증에만 사용하며 앱의 변환 의존성이 아니다.

새 회귀 검사:

```powershell
New-Item -ItemType Directory -Path status_audit -Force | Out-Null
& '.venv\Scripts\python.exe' -m pytest -q --basetemp=status_audit/new_test_run
```

개발 검사에는 `requirements-dev.txt`의 패키지와 프로젝트 루트의 `pandoc.exe`가 필요하다. `--basetemp`에는 기존 작업물이 없는 새 전용 경로를 지정한다. 회귀 검사는 `tests` 및 `experiments/tibetan_typography`에서 수집한다. 테스트용 이미지는 `tests/fixtures`에 있다. 개발 중 사용한 개인 문서·이전 스크립트·백업은 로컬 `_archive` 폴더에 보관하며 Git에 포함하지 않는다.

포터블 빌드:

```powershell
& '.venv\Scripts\python.exe' build_exe.py
```

기존 EXE는 `backups`에 복사한 뒤 교체한다. Pandoc을 EXE 안에 압축해 넣지 않고 별도 실행 파일로 배치한다. 준비된 포터블 EXE 자체를 시험할 때는 다음 진단 모드를 사용할 수 있다.

```powershell
& 'dist\ObsidianToDocx.exe' --self-test 'D:\test_output\obsidian_converter'
```

지정한 진단 폴더에 설정, DOCX/PPTX 결과, 화면 이미지, `report.json`을 생성한다. 개발 경로와 배포 경로 모두에서 공통 파일 목록으로 두 형식을 변환하는 동작을 확인했다.

## GitHub 릴리스 준비

검증한 최신 빌드는 `dist/ObsidianToDocx.exe`다. 릴리스 묶음 생성:

```powershell
& '.venv\Scripts\python.exe' scripts/prepare_release.py
```

GitHub Release에는 `release/ObsidianToDocx-windows-x64.zip`과 `release/SHA256SUMS.txt`를 첨부하고, 설명은 `RELEASE_NOTES.md`를 사용한다. ZIP에는 실행 파일, 사용 안내와 설치된 의존성의 라이선스 자료를 넣는다. 개인 설정, 문서 샘플, 글꼴 및 Pandoc 실행 파일은 포함하지 않는다. 사용자는 필요한 경우 앱에서 Pandoc을 다운로드한다.

소스 저장소에는 `src`, `resources`, `tests`, `experiments`의 소스 및 샘플, `scripts`, 빌드 설정과 문서만 올린다. `.gitignore`는 로컬 런타임·실행 파일·설정·보관 자료·생성물을 제외한다. 프로젝트 자체의 공개 라이선스는 아직 지정하지 않았다.
