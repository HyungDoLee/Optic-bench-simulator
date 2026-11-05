# Optical Bench — Python Desktop v0.3

## 720 nm 반사형 4f 예제

`Load 720 nm reflection 4f` 버튼 또는 `examples/reflection_4f_720nm.json`으로
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
requirements.txt        Pillow 이미지 표시용
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
- Screen 클릭 시 자동으로 `Screen profile` 탭으로 전환됩니다.
  - `I(u,v)/I0` 2D heatmap과 `I(u,0)/I0` 1D 곡선 표시
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
