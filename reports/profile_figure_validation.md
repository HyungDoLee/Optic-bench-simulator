# 독립 2D profile figure 구현 및 검증 보고서

작성일: 2026-11-09

작성 시각: 19:31:44 KST (UTC+09:00)

전체 검사 결과 기록 시각: 2026-11-09 19:27:41 KST (UTC+09:00).

기준 버전: `3d388d2` 이후 독립 figure 기능을 추가한 코드.

## 결과

작은 미리보기와 별도로 **MATLAB figure처럼 독립적인 2D profile 창**을 추가했다.
창 크기 변경, 여러 창 비교, Pan/Zoom, 커서 위치·강도 확인, 색상 조절과 이미지 저장을 지원한다.
기존 광학 전파, Gaussian q/ABCD, ASM/Fresnel, 수동 계산/취소와 레이저 종단은 유지했다.

최종 전체 검사: **97 passed / 0 failed / 0 error / 0 skipped**.
Linux 실행 파일에서도 실제 마우스로 독립 창 열기, 휠 확대와 Pan 드래그를 확인했다.

## 1. 사용법

1. 로컬 의존성을 `python -m pip install -r requirements.txt`로 갱신한다.
   Windows에서는 `py -3 -m pip install -r requirements.txt`를 사용할 수 있다.
2. Screen/Sample/Probe/Fourier 면을 선택한다. Wave 모드에서는 **계산하기**를 먼저 누른다.
3. **2D 프로파일 창 열기**를 누르거나 작은 heatmap을 더블클릭한다.
4. 툴바 **Pan**으로 드래그하고 **Zoom**으로 영역을 확대한다. 마우스 휠은 커서 중심 확대/축소다.
5. **Back/Forward/Home**으로 보기를 이동·복원하고, **Full FOV**로 계산 영역 전체를 확인한다.
6. **Units**에서 W/m² 또는 I/Ipeak, **Scale**에서 Linear/Log를 선택한다.
   Colormap과 Color limits도 조절할 수 있으며 잘못된 로그 범위는 적용하지 않는다.
7. 마우스를 올리면 픽셀 인덱스, 실제 u/v 좌표(mm), 원래 강도(W/m²)를 표시한다.
   Wave 데이터에는 해당 픽셀의 위상(rad)도 표시한다.
8. 툴바 **Save**로 PNG/PDF/SVG 등 Matplotlib 지원 형식으로 저장한다.

독립 창은 modal dialog가 아니므로 메인 창과 함께 조작할 수 있다. 여러 창을 동시에 열 수 있으며,
메인 장면·선택·새 계산이 바뀌어도 이미 열린 결과는 고정돼 비교에 사용할 수 있다.
Wave 결과의 Intensity/Phase 전환을 지원하며 Gaussian q에서는 계산하지 않은 위상을 만들지 않는다.

## 2. 데이터와 성능

- 212×212 미리보기를 확대하지 않고 **계산된 원본 N×N 복소 광장**에서 intensity/phase를 사용한다.
- `abs(E)**2`의 기존 단위 mW/mm²를 W/m²로 변환할 때 정확히 1000을 곱한다.
- 샘플 중심의 물리 좌표로 축과 pixel edge를 정의하고 origin=lower로 v 방향을 일치시킨다.
- 초기에는 빔이 보이는 범위를 표시하고, Full FOV는 실제 출력 Grid의 전체 영역을 보여준다.
- 창 조작은 이미 계산한 결과의 표시만 변경하며 광학 전파나 FFT를 시작하지 않는다.
- 동일 계산에서 여러 창을 열면 읽기 전용 snapshot을 공유한다. 새 계산은 별도의 snapshot을 만든다.
- 마우스 이동 때 전체 배열의 peak를 반복 계산하지 않도록 통계를 캐시한다.
- phase는 I/Ipeak<1e-6 영역을 mask 처리한다. 위상 기준은 원래 전파 결과의 기준을 따른다.

선형/로그·정규화·색상 범위를 변경해도 물리적 intensity 배열은 수정하지 않는다.
화면 확대는 계산 격자의 물리적 해상도를 늘리는 기능이 아니다.

## 3. 검증 결과

| 검사 | 결과 | 판정 |
|---|---|---|
| 알려진 복소 픽셀의 물리 강도 | 4000 W/m², 절대 오차 9.095e-13 W/m² | 통과 |
| 픽셀 위상·좌표 방향 | phase=0.7 rad, v=+0.5 mm 및 row/column 보존 | 통과 |
| 기울어진 Gaussian screen의 적분 파워 | 10 mW, 절대 오차 0 | 통과 |
| 휠 한 단계 확대의 축 span 비율 | 0.8, 절대 오차 1.110e-16 | 통과 |
| Full FOV의 물리적 폭 | 12.288 mm | 통과 |
| Pan/Back/Home/독립 창 resize | 이동·복원 및 다른 창의 보기 보존 | 통과 |
| 색상·로그·정규화·위상·저장 중 FFT/전파 호출 | 호출 시 실패하도록 막은 상태에서 모든 조작 성공 | 통과 |
| 표시 조작 전후 원래 intensity | 최대 변화 0 | 통과 |
| 툴바 Save | 실제 큰 PNG 생성 및 비어 있지 않은 이미지 확인 | 통과 |
| 새 계산 뒤 이전 창 | 이전 snapshot 보존, 새 결과와 구분 | 통과 |
| 창 닫기 및 앱 종료 | 다른 창 보존, 닫힌 창 참조·deferred draw 정리 | 통과 |

새 테스트는 `tests/test_profile_figure.py`의 5개다. 기존 92개 회귀 검사도 모두 유지했다.
측정값·오차·허용값은 [test_results.json](test_results.json), 요약은 [test_results.md](test_results.md),
전체 실행 로그는 [unittest.log](unittest.log)에 저장했다.

## 4. 발견한 문제와 수정

- 첫 GUI 검사에서 Matplotlib 3.11의 synthetic drag 이벤트에 필요한 버튼 상태와
  파일 다이얼로그 mock 경로가 맞지 않았다. 실제 backend 호출에 맞춰 테스트를 수정한 뒤 통과했다.
- 전체 97개 검사가 통과했으나 첫 보고서 저장 시 NumPy scalar bool이 JSON으로 직렬화되지 않았다.
  `tools/verify_4f.py`에서 NumPy scalar를 Python scalar로 변환하도록 보완했고,
  전체 검사를 다시 실행해 JSON/Markdown 생성과 정상 종료를 확인했다. 판정·허용 오차는 바꾸지 않았다.
- native Pan 검사에서 실제 창 위치와 입력 좌표 보정 위치가 달랐다. 검증 창을 같은 위치로 배치한 뒤
  실제 휠/드래그로 이미지가 변경되는 것을 확인했다.

## 5. 빌드와 실행 화면

환경: Linux x86_64, Python 3.13.5, Tk 8.6, NumPy 2.5.4, Pillow 12.3,
Matplotlib 3.11.2, PyInstaller 6.22.3.
PyInstaller는 **TkAgg만 명시적으로 포함**하도록 설정했다. 실행 파일에서 figure·툴바·font가 표시된다.

- [독립 figure 기본 화면](screenshots/packaged-profile-figure.png)
- [실제 휠 확대 화면](screenshots/packaged-profile-zoom.png)
- [실제 Pan 이동 화면](screenshots/packaged-profile-pan.png)
- [로그/정규화/색상 조절 화면](screenshots/independent-profile-log.png)

실행 파일: `/workspace/scratch/optic-wave-dist/OpticalBench`.
검증 상태·binary checksum·확인 항목은 [build_validation.json](build_validation.json),
빌드 로그는 [build_linux.log](build_linux.log)에 있다.
Windows EXE는 이 Linux 환경에서 만들거나 실행하지 않았다. 로컬에서는 변경된 의존성을 설치하고
소스를 실행하거나 기존 `build_windows_exe.bat`으로 다시 빌드해야 한다.

## 6. 변경 파일과 남은 범위

- `profile_data.py`: 물리 단위/좌표/위상과 읽기 전용 snapshot, Gaussian profile, 결과 시각.
- `profile_figure.py`: 독립 Tk/Matplotlib 창, 툴바, 휠, 커서, 색상/로그/위상 제어와 정리.
- `app.py`: 열기 버튼·더블클릭, 계산 결과와 연결, 여러 창과 snapshot 관리.
- `requirements.txt`, `OpticalBench.spec`: Matplotlib 의존성과 TkAgg 패키징.
- `tools/verify_4f.py`: NumPy 측정값의 보고서 직렬화 호환성.
- `tests/test_profile_figure.py`, README/사용법/보고서: 회귀 검증과 사용 안내.

일반적인 MATLAB UI의 모든 기능을 복제한 것은 아니다. ROI 적분·임의 단면 추출·CSV/NPZ 원시 데이터
내보내기와 계산 결과의 live link는 이번 범위에 포함하지 않았다. 큰 N의 서로 다른 결과를 여러 개
열면 배열/Matplotlib 이미지 메모리가 늘어난다. 새 광학 모델이나 실험 검증을 추가한 작업도 아니다.
