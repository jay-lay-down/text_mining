# PyInstaller Build Guide

## 기본 명령 (Windows CMD)
```
pyinstaller --noconfirm --onefile --windowed ^
  --name textma_ai_tool ^
  --add-data "assets\\fonts\\NanumSquareNeo-bRg.ttf;assets\\fonts" ^
  --hidden-import PyQt6.QtWebEngineWidgets ^
  --hidden-import kiwipiepy ^
  --hidden-import google.genai ^
  --hidden-import pyvis ^
  app.py
```

## 참고 사항
- QtWebEngine 리소스가 올바르게 포함되도록 PyQt6-WebEngine을 반드시 설치합니다.
- `assets/fonts/NanumSquareNeo-bRg.ttf`(또는 기존 `NanumGothic.ttf`)를 실제 폰트 파일로 교체하거나 업데이트하세요.
- 네트워크/토큰 관련 라이브러리는 동적 임포트가 있으므로 `--collect-all` 옵션을 고려할 수 있습니다.
- 빌드 전에 가상환경을 새로 만들어 `requirements.txt`를 설치한 뒤 실행하는 것을 권장합니다.
- `--onedir` 모드가 트러블슈팅에 편리할 수 있습니다. 문제가 발생하면 `--onedir`로 재시도 후 리소스 포함 여부를 점검하세요.
