옵시디언 문서 변환기 v1.0.0 — Windows x64

Markdown을 Word(DOCX) 또는 PowerPoint(PPTX)로 변환하는 포터블 앱입니다.

- 한국어·영문·티베트어 글꼴과 크기를 각각 지정할 수 있습니다.
- DOCX/PPTX 전환 시 파일 목록을 유지하고, 서식 프리셋을 저장합니다.
- 긴 PPTX 본문을 자동 분할하며 티베트어 원문과 이어지는 한국어 번역을 함께 배치합니다.
- 기존 결과를 덮어쓰지 않고 번호를 붙여 저장합니다.
- DOCX → Markdown 보조 도구를 제공합니다.

설치: `ObsidianToDocx-windows-x64.zip`을 풀고 `ObsidianToDocx.exe`를 실행하세요.
Pandoc이 없는 경우 앱의 **Pandoc 설치/업데이트** 버튼을 누르세요. 최초 다운로드에는 인터넷이 필요합니다.
Python이나 Microsoft Office는 필요하지 않습니다. 사용할 글꼴은 별도로 설치해야 합니다.

배포 ZIP에는 개인 설정, 문서 샘플, 글꼴과 Pandoc 실행 파일이 포함되지 않습니다.
무결성 확인용 SHA-256 체크섬은 `SHA256SUMS.txt`를 참고하세요.

검증: 회귀 테스트 54개 통과. 배포 ZIP에서 추출한 EXE의 DOCX/PPTX 변환 및 파일 목록 유지 검사 통과.
