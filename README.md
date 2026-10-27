# Serenity Daily Tracker (free, unofficial)

Serenity(@aleabitoreddit)의 **비공식 공개 아카이브**에 있는 종목별 상태를 매일 스냅샷으로 수집하고 GitHub Pages에 표시합니다. AI API 키나 유료 구독은 필요하지 않습니다. 단, Serenity의 실제 X 게시물 전수 수집을 제공하지는 않습니다.

## 5분 설정 (GitHub 계정 필요)

1. [GitHub](https://github.com/new)에서 `serenity-daily-tracker`라는 **Public** 저장소를 만듭니다. 공개 저장소는 데이터/코드도 공개되므로 개인 정보나 토큰을 넣지 마세요.
2. ZIP 파일을 풀어서 **폴더 안의 내용물**(`.github` 숨김 폴더 포함)을 저장소 `main` 브랜치에 업로드하세요. GitHub 웹 업로드에서 숨김 폴더가 누락되는 경우 Git을 사용하세요.
3. 저장소의 **Settings → Pages → Build and deployment → Source: GitHub Actions**로 지정합니다.
4. **Settings → Actions → General → Workflow permissions**를 `Read and write permissions`로 바꾸고 저장합니다. 조직 정책에 따라 권한이 제한될 수 있습니다.
5. **Actions → Daily Serenity tracker → Run workflow**로 첫 수집/배포를 실행합니다.
6. Actions의 작업이 성공하면 `https://<GitHub아이디>.github.io/serenity-daily-tracker/`에서 확인합니다.

자동 갱신은 `Asia/Seoul` 기준 **매일 오전 8:13**로 예약되어 있습니다. GitHub Actions는 지연/누락될 수 있고, 저장소가 오랫동안 비활성화되면 예약 실행이 중지될 수 있습니다. 수집 실패 시 기존 성공 데이터를 그대로 남깁니다.

## 실제 기능

- 최신 수집 시점 및 종목별 stance(bullish / bearish / neutral / watchlist / unclear)
- 전회 수집 대비 stance 또는 'Last seen' 값이 바뀐 종목 찾기
- 누적 언급 횟수, 원문 X 링크(아카이브에서 확인되는 경우), 상세 링크
- 날짜별 종목 분류 수 추적(수집 시작 시점부터)
- 종목/분류/변경 필터, 원문 영어 요약, 한국어 분류 안내, 번역 링크

**중요:** 한국어 요약 완역·원문 전체 수집·오늘 게시물 전수 수집·실시간 시세는 제공하지 않습니다. 본 프로젝트는 무료로 확인 가능한 제3자 페이지에 의존하고 해당 사이트의 구조/정책 변경에 영향을 받습니다. 자동 접근 허용 여부 및 해당 사이트 이용약관/robots.txt를 운영자가 확인해 주세요. 제공 사이트의 승인이 없거나 수집이 차단되면 자동 수집을 중지해야 합니다.

## 개발/테스트

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/update.py
python -m http.server 8000 -d site
```

브라우저에서 `http://localhost:8000`으로 접속합니다. 네트워크 접근이 불가능한 환경에서는 `python scripts/update.py`가 실패하며, 이는 정상입니다. 실제 데이터가 아닌 예시값을 넣어 사용자에게 전달하지 않습니다.

## 한계

- 외부 아카이브는 원저자 공식 데이터가 아닙니다. 원문 게시물에 없는 정보를 추론하지 않습니다.
- `watchlist`는 긍정이 아닙니다. `unclear`도 중립으로 간주하지 않습니다.
- '전회 대비 변경'은 실시간 게시물 업로드 시각이 아니라 수집된 아카이브의 **상태 변화**입니다.
- 최초 수집은 모든 종목을 '새로 발견'으로 표시합니다. 이후 비교가 가능합니다.
- 주식/금융 의사결정은 각 원문·공시를 직접 검증해야 합니다.
