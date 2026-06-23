# 대전어린이회관 프로그램 취소표 알림봇 요구사항

이 저장소는 `D:\requirements_djkids_cancel_alert_telegram_bot.md`의 요구사항을 기준으로 구현되었습니다.

핵심 범위:

- Telegram Bot 기반 취소표 알림 UI
- 대전어린이회관 개인 예약 페이지 조회 및 상태 파싱
- SQLite 기반 사용자, 감시 항목, 스냅샷, 알림 큐 저장
- 10분 기본 주기 모니터링
- `CLOSED` 또는 `UNKNOWN` 상태에서 `AVAILABLE` 상태로 바뀐 감시 항목 알림
- Docker 실행 및 pytest 검증
