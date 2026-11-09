# Optical Bench Simulator — 53b91f6 재평가 대응 및 수동 Wave 계산 검증

작성일: 2026-11-07. 비교 기준: Git commit `53b91f61fa024cf65b785a7ee00ea9eab0ecb5e2`.
이번 보고서는 그 이후 작업공간의 수정 코드를 검증한 결과다. 실제 광학 실험과 Windows EXE 검증은 수행하지 않았다.

## 적용 결과

Wave optics를 **계산하기 버튼으로 한 번 실행하고 프로파일을 고정하는 방식**으로 변경했다.
기존 Tk GUI, ray/ABCD/Gaussian q 계산, 720 nm SLM 예제와 누적 2500 mm 제한을 유지했다.
전체 수치·GUI 회귀 테스트는 **78 passed / 0 failed / 0 error / 0 skipped**다.
Linux 실행 파일도 다시 빌드하고 실제 마우스 클릭으로 수동 계산 및 Fourier 프로파일을 확인했다.

이 통과율은 구현된 모델의 검증 결과이며, 실제 LCOS의 홀로그램 품질이나 회절효율을 입증하지 않는다.

## 1. GUI 계산 흐름과 성능 문제 수정

이전에는 Wave 모드에서 화면 갱신이 전파 계산과 연결되어 있었고, 캐시된 광장이 있어도
전체 배열의 통계·표시 데이터를 반복 처리했다. 창 크기 변경이나 요소 조작 시 부담이 컸다.

현재 동작:

1. Screen / Sample / Probe / Fourier filter와 branch를 선택한다.
2. **계산하기**를 누르면 해당 장면·선택 경로·Grid의 복사본으로 작업 하나를 시작한다.
3. 전파 계산과 전체 배열 통계, 이미지 축소는 별도 worker에서 수행한다. Tk 위젯은 주 스레드에서만 조작한다.
4. 계산 중 버튼을 비활성화해 중복 실행과 대기 작업 누적을 막는다. UI 조작은 계속 가능하다.
5. 완료 후 212×212 이미지와 241점 곡선을 보관하고, 화면 갱신은 이 미리보기를 사용한다.
6. 설정·측정면·branch·Grid를 바꾸면 이전 결과의 측정면과 **재계산 필요**를 표시한다.
   자동 재계산은 없으며 버튼을 다시 눌러야 한다.
7. **취소**는 현재 연산 구간이 끝난 뒤 적용한다. 창을 닫을 때도 취소를 전달한다.
   실행 중인 NumPy FFT 한 개를 강제 중단하는 방식은 아니다.

Wave 모드 체크, 요소 클릭·드래그, 창 크기 변경은 FFT를 시작하지 않는다.
Gaussian q 모드의 즉시 미리보기는 유지했다. 긴 readout에는 분석 패널 스크롤을 추가했다.
샘플링 오류는 화면에 표시하고 자동 재시도하지 않는다.

GUI 테스트는 실제/가상 Tk 디스플레이에서 다음을 확인했다.

- 버튼을 누르기 전 계산 호출 0회, 중복 클릭 후 1회.
- worker를 대기시켜도 Tk 이벤트 처리 가능.
- 계산 도중 장면을 수정해도 원래 복사본으로 계산하며 추가 작업을 예약하지 않음.
- 재그리기 때 FFT 함수를 의도적으로 실패하게 만들어도 창 크기 변경·모드 전환이 정상 동작.
- Grid 변경 후 명시적으로 버튼을 눌렀을 때만 두 번째 계산 수행.
- 실패 후 재그리기에는 재시도하지 않으며 취소/닫기도 정상 동작.

## 2. 평가 항목별 처리 범위

| 평가 항목 | 이번 처리 | 남은 범위 |
|---|---|---|
| LCOS pitch와 Grid 연결 | 필요한 N과 현재 해상 가능 여부를 계산. 별도 국소 pixel-array Fourier 모델에 square-pixel sinc envelope 적용 | 전체 bench ASM에서 8 µm 픽셀을 해상하는 큰 Grid/다중 스케일 전파 |
| Gaussian과 512 px 홀로그램 크기 비교 | 직경, 조명 edge intensity, 포함 파워, beam 직경의 픽셀 수 정량화 | 실제 사용 장비의 pitch·구경·입력 빔 확정 및 GUI 연동 |
| GS + carrier + pinhole | 512×512 예시에서 GS 60회, carrier와 coherent residual, 핀홀 두 크기를 정량 비교 | 전체 경사 입사 bench의 GS 전파, sample/return image까지의 품질 검증 |
| Wave centroid와 평균 방향 | 각 전파 도착면의 중심·2σ 반경·평균 횡방향 k·평균 입사각 계산. 중심·2σ·평균 local 방향을 readout에 표시하고 +1 guide와 비교 | 실제 광장 중심을 따라 이동하는 전파 좌표계와 고 NA/tilted-plane solver |
| N/FOV 독립 수렴 | Gaussian 전파에서 N과 FOV를 각각 바꾸어 이론 반경과 비교 | 임의 GS 홀로그램의 출력 파워·형태·복소 위상 수렴은 미검증 |
| 532/720 nm | 본 예제와 GS 검증은 720 nm. 기존 532 nm 차수 위치 수식 회귀 유지 | 파장별 실측 LCOS LUT |
| Calibration/편광/시료 회절 | 기존 근사와 제약을 유지하고 미구현으로 명시 | Jones, 장비 LUT, RCWA와 고각도 collection 설계 |

## 3. 픽셀과 조명 크기: 예시 사양의 정량 결과

**8 µm pitch, 512 px는 평가에서 제시한 예시이며 실제 장비 사양으로 확정하지 않았다.**

현재 전역 Grid N=2048, FOV=6 mm의 간격은 2.9296875 µm다.
5° surface projection까지 포함하면 8 µm 픽셀당 4 samples 조건에는 **N≥3012**가 필요하며,
다음 2의 거듭제곱은 4096이다. 기존 최대 N=2048에서는 해당 전역 픽셀 해석을 지원하지 않는다.
기존 sampling guard와 band-limit/경계 파워 검사를 유지했다.

512 px × 8 µm = 직경 4.096 mm 홀로그램에 대해:

| 입력 Gaussian | 1/e² intensity 직경 | 홀로그램 edge I/Ipeak | 구경 내부 파워 비율 |
|---|---:|---:|---:|
| w=0.5 mm | 1.0 mm = 125 px | 2.676057×10⁻¹⁵ | 약 1 |
| w=2.048 mm | 4.096 mm = 512 px | 0.1353353 | 0.8646647 |

작은 빔이 구경 안에 거의 전부 들어간다는 사실은 넓은 홀로그램을 균일하게 조사한다는 뜻이 아니다.
실제 구경을 활용하려면 beam expansion과 함께 계산 FOV/해상도도 다시 정해야 한다.

## 4. 국소 GS + carrier + pinhole 검증

새 `hologram_validation.py`는 전체 bench ASM과 분리된 **정상 입사의 국소 pixel-array scalar Fourier 모델**이다.
각 물리 픽셀의 위상값으로 GS를 수행하고 해석적인 square-pixel sinc envelope를 곱한다.
primary Fourier zone만 표현하며 높은 lattice order를 추적하거나 누락 파워를 재정규화하지 않는다.

예시 입력: 720 nm, pitch 8 µm, 512×512, w=2.048 mm Gaussian, 외부 원형 입력 pupil,
f=200 mm, carrier period 128 µm, modulated coefficient 0.8 및 coherent residual coefficient 0.01.
진폭 pupil은 외부 광학 개구이며 SLM에서 진폭을 프로그래밍하지 않는다.
정상 입사 carrier 중심은 1.125 mm다. 5° bench의 1.129297 mm와 구분해야 한다.

목표는 Fourier 면의 두 Gaussian spot이다. GS 60회 후 power-normalized intensity NRMSE는
초기 **0.9999883 → 0.1388952**로 감소했다. NRMSE는
`||I/sum(I) - T/sum(T)||₂ / ||T/sum(T)||₂`다.

| 핀홀 반경 | 원하는 광장 파워 통과 비율 | 잔류 무변조광 파워 통과 비율 | coherent Fourier image NRMSE |
|---|---:|---:|---:|
| 0.2 mm | 0.04840829 = 4.840829% | 2.018252×10⁻⁵ | 1.973308 |
| 0.5 mm | 0.9600469 = 96.00469% | 2.102128×10⁻⁴ | 0.1304329 |

각 통과 비율의 분모는 해당 성분의 필터 전 primary-zone 파워다. coherent image에는 두 성분의 간섭을 포함했다.
잔류 항의 1%는 실측 효율이 아닌 입력 가정이다. 표의 비율도 실제 LCOS 소광비가 아니다.
이 예시에서 큰 핀홀은 원하는 패턴을 더 보존하지만 잔류광도 더 통과시킨다.
Gaussian blaze에 잘 맞던 Ø400 µm 핀홀이 임의 홀로그램에도 맞는다고 일반화할 수 없다.

이 검증에는 임의 sample-plane 영상 재구성, GS GUI 편집기, 제조사 SDK/LUT 또는 전체 bench의
8 µm 픽셀 전파가 포함되지 않는다. 정확한 입력과 수치는 `hologram_validation.json`에 저장했다.

## 5. Wave 방향과 기준 ray의 차이

`field_moments()`는 intensity에서 centroid/2σ 반경을, angular spectrum에서 평균 횡방향 k를 구한다.
전파 FFT의 spectrum을 재사용하며, GUI 재그리기에서 이 계산을 반복하지 않는다.
각 도착면에 평균 방향과 실제 법선에 대한 평균 입사각을 기록한다.
평균 local 방향이 5°를 초과하면 지원하는 근축 수송 범위를 벗어난 것으로 중단한다.
이는 전체 angular spectrum의 모든 성분이 근축임을 보증하는 검사는 아니다.

720 nm 기본 SLM 예제의 필터 이후 sample plane:

| 항목 | 값 |
|---|---:|
| Wave 평균 출력각 | 0.6470489594° |
| 선택 +1 order guide 각 | 0.6472030420° |
| 절대 차이 | 0.0001540826° |
| 허용 오차 | 0.002° — 통과 |

0차와 +1차가 공존하는 면의 전체 평균 방향은 +1차 방향이 아니다.
이 비교는 필터 이후 선택 차수가 지배하는 면에서 수행했다.
이 진단을 추가했지만 기존 q 기준 축을 실제 광장 중심으로 대체하지 않았으며,
공면 ray routing을 전체 3D field solver로 확장하지 않았다.

독립 Gaussian 전파 검증은 N/FOV=(256,4 mm), (512,4 mm), (512,8 mm)에서 수행했다.
500 mm 전파 후 이론 반경 0.5500226374 mm와 최대 절대 차이는 약 1.004×10⁻⁸ mm였다
(허용 2×10⁻⁶ mm). 이 수렴 결과는 임의 GS 패턴의 수렴 결과가 아니다.

## 6. 실패 원인과 유지한 제한

- 새 수동 계산 GUI 테스트의 첫 fixture는 기존 기본 장면(780 nm, 큰 빔)을 작은 FOV와 함께 사용해
  sampling guard에 걸렸다. 실제 요구 조건인 720 nm reflection 4f fixture로 수정했다.
  테스트 통과를 위해 물리 guard나 오차 허용을 완화하지 않았다.
- 추가 탐색에서 720 nm SLM 기본 배치에 digital lens f=2000 mm를 얹은 경우
  (N/FOV=1024/6, 2048/6, 2048/8)에는 ASM band-limit 파워 손실 검사가 계산을 거부했다.
  이 조건의 프로파일은 유효 결과로 제공하지 않으며, 더 큰 Grid 또는 다른 전파 방법 검토가 필요하다.
- 현재 기본 예제의 `slmPitchMm=0`은 연속 위상 근사다. 8 µm 실제 픽셀 해석으로 간주하면 안 된다.
- 실제 LCOS LUT·편광·입사각·온도 보정과 시료 재료의 회절효율은 여전히 미구현이다.
  `grating_orders()` 효율 입력은 RCWA 효율 예측이 아니다.
- 고각도 시료 회절의 수집 가능성은 기존 collection NA로 별도 판정해야 한다.
  현재 정반사 검출계가 890 nm 주기의 높은 회절각까지 수집한다고 주장하지 않는다.

## 7. 빌드와 검증 자료

환경: Linux x86_64, Python 3.13.5, Tk 8.6, NumPy 2.5.4, Pillow 12.3, PyInstaller 6.22.3.
GUI는 Xvfb에서 실제 Tk 위젯을 실행했다. 전체 78개 검사의 오차·허용값·통과 여부는
`test_results.json`과 `test_results.md`, 실행 로그는 `unittest.log`에 저장했다.

Linux 빌드: `/workspace/scratch/optic-wave-dist/OpticalBench`.
패키지 실행 후 실제 마우스로 preset 불러오기 → Fourier 면 선택 → 계산 전 빈 상태 확인 →
계산하기 클릭 → 0/+1 ROI 프로파일 표시를 확인했다.
관측 시간은 OCR 확인 비용을 포함해 약 4.25초이며 일반적인 성능 보장값이 아니다.
Windows `.exe` 빌드는 이 Linux 실행 파일과 별개이며 이번에 검증하지 않았다.

자료:

- [전체 검사 요약](test_results.md), [각 측정값과 오차](test_results.json)
- [GS 상세 보고서](hologram_validation.md), [GS 수치](hologram_validation.json)
- [빌드 검증](build_validation.json), [빌드 로그](build_linux.log)
- [계산 전 화면](screenshots/packaged-wave-before-calculate.png)
- [계산 완료 화면](screenshots/packaged-wave-return.png)

## 8. 변경 파일과 다음 단계

- `app.py`: 수동 실행, worker/취소, snapshot·stale 상태, 분석 패널 스크롤, 캐시 표시.
- `wave_view.py`: worker에서 고정 미리보기/곡선/수치 readout 준비.
- `wave_optics.py`: 취소 지점, 광장 centroid/평균 k와 면별 입사각 진단.
- `hologram_validation.py`, `tools/validate_hologram.py`: 별도 국소 GS·pixel-envelope·핀홀 검증.
- `tests/test_manual_wave.py`, `tests/test_review_diagnostics.py`, `tests/gui_helpers.py` 및 기존 GUI 테스트:
  수동 동작과 정량 물리 검증. 기존 코드를 삭제하거나 전체 엔진을 재작성하지 않았다.
- `README.md`, `docs/slm.md`, `reports/`: 사용법과 검증 증거 갱신.

다음 개발은 실제 LCOS pitch·active area·720 nm LUT와 조사 빔 크기를 확정하는 것부터 시작한다.
그 조건으로 memory-aware 다중 스케일/좌표 이동 전파를 설계하고 GS 광장의 N/FOV 독립 수렴을
파워·형태·위상까지 검증한 뒤 sample/return reconstruction으로 연결한다.
실험에서는 flat phase, carrier, 필터 통과 파워, 간단한 GS target 순서로 측정해 모델 입력을 보정한다.
