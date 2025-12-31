# 텍스트마이닝 AI 툴

PyQt6 기반 멀티페이지 데스크톱 애플리케이션 골격입니다. 업로드→전처리→버즈 피벗→텍스트마이닝(Kiwi)→감성분석(Gemini+룰)→연관/네트워크→Export 흐름을 제공합니다.

## 실행
```bash
python -m textmining_tool.app
```

## 주요 기능 개요
- QStackedWidget 기반 페이지 전환과 PandasModel을 사용한 테이블 표시
- 전처리: 컬럼 매핑, Page Type 필터, 뉴스 제외, 키 생성, 정확/유사 중복 제거
- 버즈: 기간 단위별 피벗 생성(year/half/quarter/month/week/day/hour), page_type 컬럼 옵션
- 텍스트마이닝: Kiwi 토큰화, 순수 한글 토큰 강제/이모지·감탄 제거, 불용어/품사/클린 옵션, Top50/전체 빈도/월별 Top, 워드클라우드, 누수(audit) 리포트, 빈 문서 경고
- 유해성: 비속어 맥락(Role) 기반 유해성 점수/타깃 공격 탐지, delta를 감성 점수에 컨텍스트 적용
- 감성: 문장 단위 Gemini evidence 추출(JSON), 룰 엔진으로 score_5 산출(욕설 모드 및 맥락 반영), 문서/월 집계
- 네트워크: Apriori 규칙 및 공출현 네트워크(pyvis+QWebEngineView)
- Export: 선택 시트만 Excel 저장, 빈 시트 포함 옵션(감성/유해성/audit 시트 포함)

## 빌드
PyInstaller 예시는 `build_exe.md`를 참고하세요.
- 워드클라우드/한글 표시를 위해 `assets/fonts/NanumSquareNeo-bRg.ttf`(또는 기존 `NanumGothic.ttf`)를 프로젝트 루트의 `assets/fonts`나 `textmining_tool/assets/fonts`에 복사하고, PyInstaller 번들에 포함시켜 주세요.
