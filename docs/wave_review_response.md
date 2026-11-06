# 평가표 반영 및 재검증 — 2026-11-06

## 평가를 어떻게 반영했는가

기존 Ray/ABCD 모듈과 GUI를 유지했다. 기존 27개 테스트도 유지하고, 독립적인
`wave_optics.py`와 13개 회귀 검사를 추가했다. 최종 수치/GUI 결과는 40개 통과,
실패·오류·건너뜀 0개다. 이는 해석해 및 수치 모델 검증이며 **실측 검증은 0건**이다.

| 평가 항목 | 구현/검증 | 범위 및 남은 제한 |
|---|---|---|
| P0 복소 광장 | 2D complex E, band-limited scalar ASM | 공기 중 국소 평면, 고정 FFT 창 |
| P0 실제 Fourier plane | f→lens→f ASM 및 물리 좌표의 scaled FFT | 임의 물체 FFT 가능; GUI는 선택한 기존 광선 분기 전파 |
| P1 유한 pupil/회절 | lens pupil, sample aperture, aperture의 Fourier 회절 | 경계는 픽셀화; 수차/고 NA는 미지원 |
| P1 정렬 | q, R, waist 변위, B=0 공액면 추가 검증 | wave의 decenter/큰 tilt는 계산 거부, ABCD 경로는 유지 |
| P1 sample | 복소 반사율 √R exp(iφ), 정현파 phase mask | 재료별 반사율·회절 효율을 예측하는 RCWA는 아님 |
| P2 grating | 격자 방정식, 진행 차수, 수집 NA, 입력 효율 합 검사 | 효율은 사용자/외부 모델 입력값 |
| P2 detector | 유한 원형 active area 적분, responsivity×power | 실제 센서 QE/노이즈/캘리브레이션 미지원 |
| P2 coherent splitter | unitary complex 2-port, 재결합/에너지 보존 테스트 | 함수 수준; GUI의 서로 다른 경로 자동 재결합은 미지원 |
| P3 실제 렌즈/실험 | 현재 범위에서 미구현 | 재료 분산, 수차, 편광, 실제 측정 데이터 필요 |

## 빔스플리터 45° 표시 문제

`assets/splitter.svg`의 원본은 이미 정사각 큐브 안에 +45° 대각 코팅면이
그려져 있다. 물리 모델의 angle은 **면의 법선각**이다. 정상적인 수평 입사와
수직 반사를 만드는 angle=−45°일 때 그림은 회전하지 않아야 한다.

이전 렌더러는 다른 소자와 마찬가지로 법선각을 그대로 그림에 적용해 큐브가
다이아몬드 모양이 되고 내부 코팅면이 잘못 보였다. `artwork_angle`에서
빔스플리터에만 기준각 +45°를 적용했다. 또한 Canvas의 코팅선은 실제 법선에
수직으로 그린다. 반사/투과 방향을 결정하는 물리 법선은 변경하지 않았다.
GUI 검사에서 −45° 법선의 artwork 회전 0°, 코팅선 기울기 +1을 검증했다.

## Wave 모드 사용법

1. `pip install -r requirements.txt`로 NumPy와 Pillow를 설치한다.
2. 앱에서 **Load 720 nm reflection 4f**를 누른다.
3. Screen/Sample/Probe를 선택하고 **Scalar wave profile (FFT/ASM)**를 켠다.
4. 기존 q/ABCD와 별도로 실제 복소 광장의 강도 지도·중심 단면이 표시된다.
   Wave incident는 FFT 창의 입사 출력, Collected는 원형 검출 면적 안의 출력이다.
5. Screen의 `Responsivity [A/W]`를 지정하면 PD 전류를 계산한다. 0은 미설정으로
   취급해 GUI에 `not configured`로 표시한다. 물성값을 자동으로 추정하지 않는다.

`examples/phase_sample_720nm.json`에는 period=0.5 mm, phaseDepth=1 rad인
위상 시료와 직경 1 mm, responsivity=0.5 A/W인 **가정된** 검출기 예제가 있다.
Fourier probe의 왕복 중 귀환 reading을 선택하면 시료에 의한 공간주파수 분포
변화를 볼 수 있다. 순수 위상 물체는 이상적인 정확한 영상면에서 강도 대비가
생기지 않을 수 있다. 따라서 예제에서 영상면 강도가 그대로인 것은 오류가
아니다. 이 현상과 Fourier 면의 강도 변화 둘 다 자동 검증한다.

## 정량 결과와 허용오차

최신 실제 값·오차는 `reports/test_results.json`에 기록된다. 대표 결과:

| 비교 | 이론 | 수치값 | 오차 / 기준 |
|---|---:|---:|---|
| 자유 전파 500 mm의 w | 0.550022637352 mm | 0.550022647387 mm | 약 1.00e-8 mm; ASM 고차항, 허용 2e-6 mm |
| 4f Fourier waist | 0.091673247221 mm | 0.091673247241 mm | 약 2.01e-11 mm |
| 4f sample waist | 0.25 mm | 0.249999999999 mm | 약 6.02e-13 mm |
| sample→detector B | 0 mm | 0 mm | 0; waist와 별도로 검증 |
| sample→detector A | −2 | −2 | 0 |
| 10 mm L1 이동 시 R | 967.479986673 mm | 967.479986673 mm | 약 1.59e-12 mm |
| a=w aperture 통과율 | 0.864664716763 | 0.864348036659 | 0.000316680105; 픽셀 경계 허용 0.002 |
| 유한 detector P | 8.646647167634 mW | 8.643480366587 mW | 0.003166801047 mW; 허용 0.02 mW |
| λ=720 nm, Λ=890 nm 1차 회절 | 53.997248272° | 53.997248272° | 격자 방정식 |
| 위 1차 회절 수집 최소 NA | 0.808988764045 | 0.808988764045 | NA=0.8에서 미수집, 0.81에서 수집 |

격자 효율 테스트에 사용한 {−1:0.2, 0:0.4, +1:0.2}는 예시 입력값이다.
Ni/Cu 시료의 실제 효율이 20/40/20%라는 뜻이 아니다.

256→512 격자 수렴, FFT 파워 정규화, aperture 후 회절 wing, Fourier peak의
물리 좌표, low-pass mask 효과, coherent splitter dark/bright port와 에너지 보존도
검증한다. 허용오차는 픽셀 경계/근축해와 exact scalar ASM의 차이 등을 구분해
지정했으며, 실패를 숨기기 위한 재정규화나 assertion 비활성화는 하지 않았다.

## 샘플링, 좌표와 지원 범위

- 길이 mm, 파장 nm, 출력 mW. |E|² 단위는 mW/mm²이고 면적 적분해 출력을 구한다.
- exp(−iωt), forward ASM exp(+ikz), lens exp(−ikr²/2f) convention을 쓴다.
  source q와 대응하는 입사장의 곡률 부호도 포함했다.
- GUI 기본 격자는 512², 폭 4 mm, dx=7.8125 µm. FFT는 주기 경계다.
- 전파 위상의 주파수 샘플링 한계로 band-limit를 적용한다. 유의한 스펙트럼
  손실이나 창 가장자리의 파워가 검출되면 오류로 중단한다. 손실을 강제로
  재정규화하지 않는다. 렌즈 위상의 illuminated support도 샘플링 검사한다.
- 주기당 최소 8 pixel 미만의 sample mask는 거부한다. 따라서 **890 nm 시료를
  mm-scale 격자 위에 직접 그려 계산하지 않는다.** 890 nm 차수 방향은 별도의
  격자 방정식 함수로 계산한다. 실제 sub-µm 효율 계산에는 국소 RCWA가 필요하다.
- 광선이 안내한 하나의 분기만 전파한다. 회절광이 새 렌즈를 찾아가는 경로나
  서로 다른 branch의 coherent 재결합은 아직 없다. thin lens/sample/probe는
  근수직·중심 입사만 지원하며, 지원 범위 밖이면 GUI에 오류 이유를 표시한다.
- field는 beam-local 좌표다. 반사 시 u 방향을 반전하며, 전역 위상 exp(ikL)은
  생략한다. 간섭 함수 입력은 같은 평면/좌표/파장으로 정렬하고 상대 위상을
  명시해야 한다. 현 GUI에서 정량적인 interferometer를 구성했다고 해석하면 안 된다.
- Gaussian q envelope/waist는 clipping 이후에도 이상적인 참고값이다. Wave 모드는
  실제 field의 2σ 크기와 실제 peak를 별도로 표시한다. 하단 그래프는 여전히 q 모델이다.
- 2500 mm 누적 경로 제한은 기존 tracer에서 유지하며, wave 엔진은 그 범위 안의
  실제 도달 reading만 사용한다.

## 빌드 및 발견한 패키징 문제

Linux에서 기존 `OpticalBench.spec`를 사용해 실제 단일 실행 파일을 빌드했다.
첫 패키지 실행은 Pillow의 동적 모듈 `PIL._tkinter_finder` 누락으로 실패했다.
원본 오류는 `reports/history/packaged_initial_failure.log`에 보존했다.
spec의 hiddenimports에 해당 모듈을 추가하고 Windows bat도 같은 spec을 사용하게
수정했다. 빌드 로그와 실행 파일의 검증 결과는 `reports/build_linux.log`,
`reports/build_validation.json`을 확인한다.

Windows EXE는 이 Linux 환경에서 빌드/실행했다고 주장하지 않는다. Windows에서는
기존 `build_windows_exe.bat`을 실행해 `dist/OpticalBench.exe`를 만든다.

## 남은 개발 단계

1. 실제 재료 n+ik, 높이, duty cycle, 격자 형상 및 입사 편광을 입력받는 RCWA
   sample-response adapter와 외부 기준 데이터 비교.
2. Jones/Stokes 편광, 실제 splitter r/t 위상과 유리 내부 경로, 전역 위상을 보존하는
   branch 재결합, tilted/decentered field 좌표변환.
3. scaled/padded ASM, sampling 자동 설계, non-Gaussian field가 aperture에 의해
   분리되더라도 새 경로를 탐색하는 하이브리드 라우팅.
4. 실제 검출기 QE·잡음·포화·픽셀 적분, 렌즈 EFL/수차/코팅의 카탈로그 및 실측 검증.

실험 측정값을 제공받기 전까지는 "실제 실험과 검증 완료"라고 표현하지 않는다.
