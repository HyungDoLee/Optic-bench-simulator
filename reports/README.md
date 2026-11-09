# 검증 보고서

최신 기능 보고서: [독립 2D profile figure 구현 및 검증](profile_figure_validation.md).
물리 모델 보고서: [Fresnel forward diffraction 및 레이저 귀환광 종단 검증](fresnel_forward_validation.md).
전체 테스트: [요약](test_results.md), [측정값·오차·허용값](test_results.json).

## 날짜·시간 표기 규칙

앞으로 사람이 읽는 보고서의 제목 아래에 날짜와 시각을 분리해서 표시한다.
시간대는 한국 표준시(Asia/Seoul, KST, UTC+09:00)로 통일한다.

```text
작성일: YYYY-MM-DD
작성 시각: HH:mm:ss KST (UTC+09:00)
```

- 날짜는 `2026-11-09`, 시각은 24시간제 `18:06:26`처럼 쓴다.
- 작성 시각과 테스트 실행 시각이 다르면 구분해서 표시한다.
- 기존 결과의 표시 형식만 바꿀 때는 원래 검사 시각을 보존한다.
- 기존 보고서를 수정하면 필요한 경우 `최종 수정일`과 `최종 수정 시각`을 같은 형식으로 추가한다.
- JSON의 `generated_at`은 자동 처리를 위해 UTC offset을 포함하는 ISO 8601 형식을 유지한다.
- 과거 실패 로그와 스냅샷은 당시 기록을 유지한다.

`tools/verify_4f.py`와 `tools/validate_hologram.py`의 Markdown 출력에도 이 규칙을 적용한다.
