# Optical Bench — Python Desktop v0.3

## 계산 진행 표시와 GUI 정리

**빔 분석** 패널을 `01 계산 설정 → 02 계산 실행 → 03 결과 보기` 순서로 정리했습니다.
계산 중에는 단계 진행률·경과 시간이 표시됩니다. 이전에 동일한 설정으로 성공한 기록이 있을 때만
예상 남은 시간을 표시하며, 첫 계산에서는 경과 시간만 확인할 수 있습니다.
진행률은 완료한 계산 단계의 비율이며 남은 시간의 비율을 뜻하지 않습니다.

- 상단 상태 배지는 다른 탭에서도 경과 시간을 표시합니다. 누르면 빔 분석으로 돌아갑니다.
- 취소·실패는 완료와 구분하며, 성공한 결과를 받아야 100%가 됩니다.
- 왼쪽 요소 추가 버튼은 2열로 정리하고, 상태별 색상과 버튼 간격을 통일했습니다.
- 1D 단면과 q/ABCD/광파워는 **1D 단면 보기 / 상세 수치**를 펼쳐 확인합니다.
- 계산은 수동 실행하며, 화면 갱신이나 창 조작으로 자동 재계산하지 않습니다.

[로딩바·시간 표시·GUI 검증 보고서](reports/progress_gui_validation.md)를 참고하세요.

## 독립 2D profile figure

빔 분석에서 **2D 프로파일 창 열기**를 누르거나 작은 heatmap을 더블클릭하면,
MATLAB figure처럼 별도 창에서 원본 해상도의 결과를 볼 수 있습니다.
Wave 모드에서는 먼저 **계산하기**를 눌러 결과를 만드세요. Gaussian q도 지원합니다.

- 자유로운 창 크기 조절, 여러 결과 창을 동시에 열어 비교.
- 툴바 Pan/Zoom/Home/Back/Forward, 마우스 휠로 커서 중심 확대·축소.
- mm 좌표와 픽셀의 실제 강도 W/m² 확인, 선형/로그 표시, 정규화와 colormap/color limits 조절.
- Wave 결과의 phase 보기와 색상 범례, 툴바 Save로 PNG/PDF/SVG 등 저장.
- 각 창은 열었을 때의 고정 결과를 유지합니다. 확대·이동·저장은 광학 전파/FFT를 다시 실행하지 않습니다.

새 의존성 **Matplotlib**을 포함해 `python -m pip install -r requirements.txt`로 갱신하세요.
[독립 figure 구현·검증 보고서](reports/profile_figure_validation.md)를 참고하세요.

## Fresnel forward diffraction

**GS 없이 입력한 SLM 위상이 만드는 광장을 전파합니다.**
`720 nm · LCOS SLM 4f`는 `전파 방식: Fresnel`, 계산 격자 512×512/FOV 6 mm로 시작합니다.
Screen·Sample·Fourier 면 선택 → **계산하기** → `2D display: Intensity / Phase`로 확인하세요.
보기 전환은 FFT를 다시 실행하지 않습니다. `examples/slm_fresnel_720nm.json`도 같은 설정입니다.

Fresnel 이상 모드는 렌즈·시료·검출기의 clipping과 pinhole 차단을 생략하고,
자유 전파/렌즈의 Fresnel 적분을 계산합니다. SLM active area·pixel response는 유지합니다.
입출력 N은 같아도 샘플 간격/FOV는 달라지며 출력 좌표는 readout에 표시합니다.
기존 유한 구경 계산은 `전파 방식: ASM`으로 선택할 수 있습니다.
레이저에 되돌아온 경로는 레이저에서 흡수 종단되며 뒤쪽으로 연장되지 않습니다.

[Fresnel 구현·수치/GUI 검증 보고서](reports/fresnel_forward_validation.md)를 참고하세요.
GS는 별도 선택 검증 코드로만 남겨두고 GUI의 forward 경로에서 호출하지 않습니다.

## SLM 추가

현재 기본 배치는 **5° 경사 입사 LCOS → carrier → Fourier spatial filter → 시료**입니다.
LCOS 경로 분리용 splitter를 제거하고, 시료 반사 검출용 pick-off만 남겼습니다.
ASM 모드에서 0차/+1차 경로와 각 ROI의 광파워를 별도로 표시합니다. 입사각과 차수 선택은
서로 다른 기능입니다. [현재 배치·가정·검증·제한](docs/slm.md)을 먼저 참고하세요.

**720 nm · LCOS SLM 4f** 또는 **+ LCOS SLM**으로 **반사형 phase-only LCOS**를 추가합니다.
위상 패턴과 균일 반사 효율·위상 양자화·pixel pitch·fill factor를 설정할 수 있고
위상 이미지 import와 preview를 지원합니다. 변조 결과는 **Scalar wave profile**로
Fourier 면/Screen에서 확인하세요. [SLM 사용법·샘플링·한계](docs/slm.md)를 참고하세요.

## Scalar wave optics 업데이트

기존 Gaussian q 모드를 유지하면서 **Scalar wave profile (FFT/ASM)** 옵션을 추가했습니다.
유한 렌즈 pupil·회절·복소 시료 반사·유한 검출 면적을 별도 파동 엔진으로 계산합니다.
파동 모드는 Screen·Sample·Probe·Fourier filter를 선택한 뒤 **계산하기**를 눌러
한 번 실행합니다. 모드 선택·드래그·파라미터 수정·창 크기 변경으로 FFT를 자동 실행하지
않습니다. 계산은 백그라운드에서 실행하며 **취소**할 수 있습니다. 완료된 프로파일은
고정되고, 설정을 바꾸면 **재계산 필요**가 표시됩니다. 새 결과는 다시 버튼을 눌러 얻습니다.
빔스플리터 그림의 45° 기준 방향도 수정했습니다. 실행 전 NumPy를 포함한 의존성을
`python -m pip install -r requirements.txt`로 갱신하세요.

[평가표 반영·수치 검증·지원 범위](docs/wave_review_response.md)를 참고하세요.
[53b91f6 재평가 대응·수동 계산·GS 검증 보고서](reports/review_v53b91f6_response.md)에는
이번 변경, 픽셀/빔 크기 비교, 핀홀 통과율과 남은 제약을 정리했습니다.
`examples/phase_sample_720nm.json`으로 위상 시료와 유한 검출기 예제를 열 수 있습니다.
아래의 Gaussian 모델 한계 설명은 기본 q 모드에 해당하며, 파동 모드도 RCWA·편광·
임의 branch 간 간섭과 실제 시료 재료 효율은 아직 계산하지 않습니다.

## 720 nm 반사형 4f 예제

`720 nm · Reflection 4f` 버튼 또는 `examples/reflection_4f_720nm.json`으로
200/100 mm 릴레이를 불러옵니다. 시료의 이상적 정반사와 가상 object/Fourier
측정면을 추가했으며, Screen·Sample·Probe 클릭 시 프로파일과 q/ABCD를 표시합니다.
시료 waist 반경은 0.25 mm, 반사광 검출기는 시료의 공액면에 있습니다.

설계·이론·metric 부품 후보·물리 모델 한계는 [4f 설계 문서](docs/4f_design.md),
검증 결과는 [테스트 보고서](reports/test_results.md)를 참고하세요.

```powershell
py -3 tools/verify_4f.py --output reports
```

GUI 테스트는 디스플레이가 필요하며, 없으면 건너뜀으로 기록됩니다.

단일 PC에서 실행되는 **Python / Tkinter** 기반 광학 breadboard 설계 프로그램입니다. 웹 브라우저/HTML/웹서버가 필요 없습니다. UI는 밝은 배경의 단순한 데스크톱 스타일이며, 사용자가 제공한 `svg.zip`의 도형을 활용합니다.

## Windows + VS Code 실행

1. [Python](https://www.python.org/downloads/)을 설치합니다. (Windows에서 Tkinter는 일반적인 Python 설치에 기본 포함됩니다.)
2. 이 프로젝트 폴더를 압축 해제하고 VS Code에서 폴더로 엽니다.
3. VS Code 터미널에서 다음 명령을 실행합니다.

```powershell
py -3 -m pip install -r requirements.txt
py -3 app.py
```

또는 `run_windows.bat`을 더블클릭합니다. (`Pillow`를 먼저 설치해야 합니다.) 설치 후에는 `OpticalBench.pyw`를 더블클릭해 콘솔 창 없이 실행할 수도 있습니다.

**개별 EXE를 만들려면 Windows PC에서** `build_windows_exe.bat`을 실행하세요. 빌드 후 `dist\OpticalBench.exe`가 생성됩니다. PyInstaller는 일반적으로 빌드 대상 OS에서 실행해야 하므로, 이 ZIP에 Windows `.exe` 자체는 포함되지 않습니다.

## 구성

```
app.py                 Tkinter 편집기/그래프/프로퍼티/화면 프로파일
optics.py              순차 독립형 계산 엔진 (파이썬 기본 라이브러리만 사용)
assets/                 svg.zip에서 추출한 원본 SVG 및 실행용 PNG
examples/               JSON 예제
wave_optics.py         별도 scalar ASM/복소 광장 엔진
fresnel_optics.py      이상적 Fresnel/Collins 전파와 초점면 scaled FFT
wave_view.py           수동 계산 결과의 고정 미리보기 준비
wave_progress.py       단계 진행·경과 시간·이전 동일 설정 기반 예상 시간
profile_data.py        독립 figure의 원본 해상도/물리 단위 고정 데이터
profile_figure.py      Matplotlib/Tk 독립 figure와 확대·이동·색상·저장
hologram_validation.py 국소 pixel-array/GS 검증 모델
requirements.txt        NumPy·Pillow·Matplotlib
OpticalBench.pyw        Windows GUI 더블클릭 실행
run_windows.bat         소스 프로그램 시작
build_windows_exe.bat   Windows EXE 빌드
.vscode/launch.json     VS Code Run and Debug 구성
tests/test_optics.py    물리 계산 회귀 테스트
```

## 기본 동작

- `Laser`, `Thin lens`, `Mirror`, `Beam splitter`, `Screen` 추가.
- 부품 드래그, 위치/각도/f/diameter 등 파라미터 수정 후 `Apply parameters`.
- R/Shift+R 5도 회전, Delete 삭제(입력칸에 포커스가 없을 때).
- 조정하면 경로·Gaussian envelope·waist 위치가 재계산됩니다.
- Screen 클릭 시 자동으로 `빔 분석` 탭으로 전환됩니다.
  - Gaussian q 모드는 프로파일을 즉시 표시하며, Scalar wave 모드는 **계산하기**로 갱신
  - 중심 ray의 도달 경로길이, 입사각, 1/e² 반경, 투영 반경, 출력과 peak irradiance
  - Beam splitter에서 Screen으로 여러 경로가 올 경우 branch를 드롭다운으로 선택
- JSON 저장/열기 (이전 v0.2 Scene JSON과 호환).
- 전체 경로 제한은 **광원부터 각 분기까지 누적 2500 mm**입니다. 그 이상 경로 탐색/ABCD 계산을 수행하지 않습니다. 테이블 가장자리에 먼저 도달하면 거기서 종료됩니다.

## 계산 방식과 한계

1. **2D non-sequential ray tracing:** 광학 요소를 자동으로 교차 탐색하고 미러 반사, 빔스플리터 분기를 처리합니다.
2. **ABCD Gaussian beam:** 자유 전파 `q' = q + L`, thin lens `q' = q/(1-q/f)`; `1/q=1/R - i λ/(π w²)`.
3. **Screen intensity:** 이상적인 circular Gaussian beam. 입사각 `θ`에서는 스크린 위 수평 투영 반경이 `w/|cos θ|`가 됩니다. 중심 위치 offset도 반영합니다.

**중요한 한계:** 현재 Screen 강도 지도는 full Fresnel/FFT 해석이 아니며, 구경에 따른 clipping, 회절, astigmatism, 수차, 서로 다른 광경로 사이 간섭, 경로 위상은 반영하지 않습니다. `Power (input)`은 Screen 유한 구경으로 적분한 검출 출력이 아닌 도달 빔의 입사 광출력입니다. Envelope는 시각적으로 확인하기 쉽도록 화면에서만 확대해 표시하며, 계산값은 원래 반경을 사용합니다. 렌즈를 비스듬히 지나거나 큰 각도로 꺾이는 상태는 근축 가정 밖일 수 있습니다. 화면에 표시하는 2D 강도 map은 Screen 중심에 대한 관측 창이며, 실제 Screen의 구경 윤곽을 표시하는 것은 아닙니다.

## 테스트

```powershell
py -3 -m unittest discover -s tests -v
```

수치 모델 및 2.5 m 누적 제한 검사. UI는 Python 데스크톱 창으로 테스트합니다.

## SVG

`assets/*.svg`는 사용자 제공 SVG 번들에서 가져온 부품 그림입니다. Tkinter가 SVG를 기본 렌더링하지 않으므로 SVG를 PNG로 변환해서 `assets/*.png`로 같이 포함했습니다. 원본 SVG 파일도 보관합니다. 저작권/재배포 라이선스는 사용자가 확인해야 합니다.
