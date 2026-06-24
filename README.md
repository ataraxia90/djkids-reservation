# 대전어린이회관 취소표 Telegram 알림봇

대전어린이회관 개인 예약 페이지를 주기적으로 조회해서, 사용자가 감시 등록한 프로그램이 `마감`에서 `예약하기` 또는 `예약가능` 상태로 바뀌면 Telegram으로 알려주는 Bot입니다.

자동 예약, 로그인, 개인정보 입력, CAPTCHA 우회는 하지 않습니다. 사용자는 알림을 받은 뒤 공식 예약 페이지에서 직접 예약해야 합니다.

## 기능 요약

- Telegram 명령어: `/start`, `/help`, `/watch`, `/list`, `/delete`, `/settings`
- 비공개 운영 기본값과 Telegram 사용자 ID 화이트리스트
- `httpx + BeautifulSoup` 기반 예약 페이지 조회 및 파싱
- `CLOSED`, `AVAILABLE`, `UNKNOWN`, `ERROR` 상태 정규화
- SQLite 저장: 사용자, 감시 항목, 프로그램 스냅샷, 알림 큐, 알림 로그, 조회 로그
- APScheduler 기반 기본 1분 주기 모니터링
- 중복 알림 방지 및 알림 후 감시 항목 자동 비활성화
- Docker 및 docker compose 실행 지원

## Telegram Bot 생성

1. Telegram에서 `@BotFather`를 엽니다.
2. `/newbot`으로 Bot을 생성합니다.
3. 발급받은 Bot Token을 `.env`의 `TELEGRAM_BOT_TOKEN`에 입력합니다.
4. 본인의 Telegram 사용자 ID를 `ADMIN_TELEGRAM_IDS`와 `ALLOWED_TELEGRAM_USER_IDS`에 입력합니다.

사용자 ID는 Telegram의 user info Bot 등을 통해 확인할 수 있습니다.

## 환경변수 설정

```bash
cp .env.example .env
```

필수로 채울 값:

```env
TELEGRAM_BOT_TOKEN=123456:replace_me
ADMIN_TELEGRAM_IDS=123456789
ALLOWED_TELEGRAM_USER_IDS=123456789
```

주요 설정:

```env
ALLOW_PUBLIC_SIGNUP=false
PORT=8080
RESERVATION_MONTH_COUNT=3
CHECK_INTERVAL_MINUTES=1
CHECK_JITTER_SECONDS=60
MAX_WATCH_TARGETS_PER_USER=5
DATABASE_URL=sqlite:///./data/app.db
USE_PLAYWRIGHT=false
```

초기값은 비공개 운영입니다. `ALLOW_PUBLIC_SIGNUP=false`일 때는 `ADMIN_TELEGRAM_IDS` 또는 `ALLOWED_TELEGRAM_USER_IDS`에 포함된 사용자만 사용할 수 있습니다.

## Docker 실행

```bash
docker compose up -d
```

SQLite DB는 `./data`에 저장됩니다.

로그 확인:

```bash
docker compose logs -f
```

중지:

```bash
docker compose down
```

## Render 무료 Web Service 실행

Render 무료 플랜에서는 Background Worker 대신 Web Service로 배포하고, 외부 ping 서비스가 `/health`를 주기적으로 호출하도록 운영할 수 있습니다.

주의: 무료 Web Service의 로컬 파일은 재시작, 재배포, 스핀다운 시 사라질 수 있습니다. SQLite DB(`./data/app.db`)에 저장된 감시 목록도 유실될 수 있으므로 안정 운영에는 유료 Persistent Disk 또는 외부 DB를 사용하세요.

1. Render Dashboard에서 `New` → `Web Service`를 선택합니다.
2. GitHub 저장소를 연결합니다.
3. Runtime은 `Docker`를 선택합니다.
4. Dockerfile Path는 기본값 `./Dockerfile`을 사용합니다.
5. 환경변수를 설정합니다.

```env
APP_ENV=production
TIMEZONE=Asia/Seoul
TELEGRAM_BOT_TOKEN=123456:replace_me
ALLOW_PUBLIC_SIGNUP=false
ADMIN_TELEGRAM_IDS=[123456789]
ALLOWED_TELEGRAM_USER_IDS=[123456789]
DATABASE_URL=sqlite:///./data/app.db
RESERVATION_MONTH_COUNT=3
CHECK_INTERVAL_MINUTES=1
CHECK_JITTER_SECONDS=60
```

Render가 `PORT` 환경변수를 자동으로 제공합니다. 앱은 `/health`와 `/`에서 `ok`를 응답합니다.

배포 후 UptimeRobot 같은 외부 모니터링 서비스에서 다음 URL을 5분마다 호출하도록 설정합니다.

```text
https://<render-service-name>.onrender.com/health
```

## 로컬 개발

Python 3.11 이상을 사용합니다.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python -m app.main
```

`python -m app.main`은 `TELEGRAM_BOT_TOKEN`이 설정되어 있어야 실행됩니다.

## 테스트

```bash
python -m pytest
```

테스트는 외부 사이트나 Telegram API에 의존하지 않고 fixture HTML과 서비스 로직을 검증합니다.

## 조회 및 파싱 방식

현재 사이트는 예약 페이지의 JavaScript가 `/resve/indvdl/s0_getList.do` JSON endpoint를 호출해 목록을 렌더링합니다. Bot은 먼저 공식 예약 페이지의 form 값을 읽고, 같은 endpoint를 일 단위로 조회해 프로그램 목록을 구성합니다.

HTML fixture 파서는 보조 경로와 테스트 용도로 유지합니다. 파서는 예약 페이지의 table row, 프로그램 목록, 예약 목록 후보를 순회하며 다음 값을 추출합니다.

- 날짜
- 프로그램명
- 회차 또는 시간
- 원본 상태
- 정규화 상태
- 원본 텍스트
- 출처 URL

사이트 DOM이나 endpoint 응답이 바뀌면 `app/djkids/fetcher.py`, `app/djkids/json_parser.py`, `app/djkids/parser.py`를 조정하면 됩니다.

## 운영 주의사항

- 기본 조회 주기는 1분입니다. 대상 사이트에 부담을 주지 않도록 운영 상황에 맞춰 조정하세요.
- 사용자 수와 무관하게 전역 조회 1회 후 DB 스냅샷과 감시 항목을 매칭합니다.
- 실패 시 무한 즉시 재시도하지 않고 제한된 재시도와 backoff를 사용합니다.
- Bot Token은 코드, README, 로그에 넣지 말고 `.env`로만 관리하세요.
- SQLite DB와 백업 파일을 공개 저장소에 올리지 마세요.

## MVP 제한사항

- 관리자 명령어(`/allow`, `/block`)는 향후 확장 범위입니다.
- Playwright fallback 인터페이스는 제공하지만 기본 Docker 이미지에는 브라우저 런타임을 포함하지 않았습니다.
- 실제 사이트 endpoint 응답이 바뀔 수 있으므로 첫 운영 전 `/watch`로 파싱 결과를 확인해야 합니다.
- 웹 프론트엔드, 결제, 로그인, 자동 예약은 범위에서 제외되어 있습니다.
