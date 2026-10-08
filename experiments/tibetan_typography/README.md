# 티베트어 서식 분리 실험

2026-10-08. 기존 앱과 분리된 검증용 코드이며 `src`와 배포 EXE는 수정하지 않았다.

## 확인한 결과

- 기존 DOCX 후처리는 한 run에 티베트어가 있으면 함께 들어 있는 한국어와 영문도 티베트어 글꼴·크기로 변경한다. 재현 테스트를 포함했다.
- 기존 PPTX 후처리는 `size_cs`와 `font_tibetan`을 반영하지 않는다. 재현 테스트를 포함했다.
- 새 방식은 Unicode U+0F00–U+0FFF의 티베트어 구간을 분리한 뒤 해당 구간에만 지정 글꼴과 크기를 적용한다. 티베트어 모음·아래첨자·문장부호·숫자를 포함하며 Wylie는 영문으로 유지한다.
- DOCX의 본문·표·하이퍼링크·각주·머리말·꼬리말, PPTX의 제목·본문·표·각주 슬라이드를 검사했다.
- 텍스트 순서, 공백, 굵게, 기울임, 링크 대상, 줄바꿈과 탭을 유지하는 검증을 포함했다. 두 번 적용해도 결과가 달라지지 않는지 검사했다.
- 폰트 이름과 크기 설정 두 조합을 자동검증했다. 다른 글꼴 이름을 저장할 수 있다는 검사와 실제 설치된 글꼴로 렌더링하는 검사는 구분한다.

## 실제 Office 표시 확인

설치된 Microsoft Word와 PowerPoint에서 비교 파일을 읽기 전용으로 열어 PDF를 생성했다. 새 DOCX 1페이지와 새 PPTX 7슬라이드의 렌더링 이미지를 검사했다.

| 파일 | 일반 본문 | 티베트어 본문 | 제목 일반 / 티베트어 |
|---|---:|---:|---:|
| DOCX | 12pt | 20pt | 24pt / 40pt |
| PPTX | 20pt | 32pt | 32pt / 51.2pt |

글꼴은 Arial / Malgun Gothic / Microsoft Himalaya로 지정했다. 한국어·영문이 티베트어 크기로 함께 커지지 않으며, 공백 없는 혼합문장에서도 티베트어 모음과 아래첨자가 유지되는 것을 확인했다.

출력은 `output/tibetan_corrected.docx`, `output/tibetan_corrected.pptx`이다. `current_app.*`는 같은 입력에 기존 후처리를 적용한 비교본이다.

## 재실행

프로젝트 루트에서:

```powershell
& '.venv\Scripts\python.exe' -m pytest experiments/tibetan_typography/test_prototype.py -q --basetemp=status_audit/tibetan_fresh_run
& '.venv\Scripts\python.exe' -m experiments.tibetan_typography.run_experiment
& 'experiments\tibetan_typography\render_office.ps1'
```

pytest의 `--basetemp`는 기존 폴더를 정리하므로 매번 새로운 전용 경로를 지정한다. Office 렌더링은 Word와 PowerPoint가 설치된 Windows에서만 실행된다. 마지막 명령은 비교 PDF를 다시 생성한다.

## 적용 전 남은 범위

- 이번 실험은 문자별 서식 적용을 검증한 것이다. 전체 앱에 통합하거나 EXE를 다시 빌드하지 않았다.
- 글꼴이 설치되어 있지 않으면 Office가 다른 글꼴로 대체할 수 있다. 실제 표시 검증은 설치된 Microsoft Himalaya 기준이다. Monlam 글꼴의 표시 검증은 별도로 필요하다.
- 제목 크기는 본문과 티베트어 본문의 비율로 확대하는 실험 정책이다. 앱의 제목 단계별 크기와 사용자가 지정할 정책은 통합할 때 연결해야 한다.
- 긴 문서를 한 슬라이드에 몰아 넣으면 글자 확대 후 넘침이 생긴다. PPTX 검증본은 제목으로 내용을 분할했으며, 자동 분할·텍스트 상자 크기·줄간격 처리는 이 실험에 포함하지 않았다.
- 차트, SmartArt, 수식, 슬라이드 마스터, 필드(a:fld), 특수 삽입 객체의 글꼴까지 처리하는 실험은 아니다.
- 직접 OOXML을 다루므로 변경 노드의 속성 순서도 정렬했다. 향후 다양한 실제 문서의 회귀 검증을 유지해야 한다.
