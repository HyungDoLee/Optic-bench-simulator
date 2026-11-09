# Fresnel forward diffraction 및 레이저 귀환광 종단 검증

작성일: 2026-11-09

작성 시각: 18:07:07 KST (UTC+09:00)

기준 commit: `2221805` 이후 작업공간 수정본.

## 결과와 범위

요청에 따라 **GS 없이 주어진 SLM 위상의 Fresnel 회절/Fourier 변환을 확인하는 모드**를 추가했다.
이상적인 렌즈와 근축 scalar 광장을 사용하고, 렌즈/시료/검출기의 clipping과 pinhole 차단은 생략한다.
기존 ASM 유한 구경 모드, GUI, ABCD/q 기준 계산, 720 nm와 누적 2500 mm 제한을 유지했다.
추가 요청에 따라 레이저로 되돌아온 빔은 레이저에서 끝나며 뒤쪽으로 전파하지 않는다.

최종 전체 검사: **92 passed / 0 failed / 0 error / 0 skipped**.
검사 결과 기록 시각: 2026-11-09 17:59:39 KST (UTC+09:00).
Linux 실행 파일을 다시 빌드하고 실제 마우스/키보드로 계산과 위상 표시를 확인했다.
Windows EXE와 실제 광학 실험은 검증하지 않았다.

## 1. 구현한 Fresnel 전파

`fresnel_optics.py`는 Gaussian q만 계산하는 엔진이 아니다. 위상 변조 이후의 **실제 2D 복소 배열**에
Collins/Fresnel 적분을 적용한다. 자유 전파와 중심 thin lens를 phase screen 사이의 ABCD 블록으로
합성하고, 그 행렬로 Fresnel 적분 kernel을 정한다. 이 과정은 중간 렌즈 chirp를 불필요하게 거친
격자에서 표본화하는 문제를 피한다. 아직 변조되지 않은 입사 Gaussian만 첫 phase screen까지
복소 q의 해석해로 평가한다. SLM 이후에도 Gaussian으로 강제 근사하지 않는다.

`B != 0`인 블록에서, 전체 축방향 piston을 제외한 scalar field는 다음과 같다.

```text
Eout = exp(i*pi*D*r_out²/(lambda*B)) / (i*lambda*B)
       × Fourier{ Ein * exp(i*pi*A*r_in²/(lambda*B)) }
dx_out = lambda*abs(B) / (N*dx_in)
```

DFT의 dx² 면적 요소와 복소 prefactor를 포함해 절대 광파워 단위를 유지한다.
잘못된 파워를 사후 정규화해 맞추지 않는다. B<0이면 Fourier 부호를 반대로 처리한다.
`B=0`의 정확한 결상면은 배율 A, intensity Jacobian과 출력 이차 위상을 적용한다.
음의 배율은 두 횡방향 좌표를 반전한다.

전초점면 → 렌즈 → 후초점면에서는:

```text
P(f) L(f) P(f) = [[0, f], [-1/f, 0]]
E_F = -i/(lambda*f) * Fourier{ E_in }
```

따라서 이 조건에서는 scaled FFT가 Fresnel 적분의 결과다. 초점에서 벗어나면 A/D chirp가
남도록 구현했다. 렌즈 바로 앞을 입력으로 삼아 후초점면을 계산하는 경우에도 출력 이차 위상을
생략하지 않는다. 상대적인 공간 위상은 보존하며, 서로 다른 branch의 간섭은 다루지 않는다.

## 2. 샘플 수와 물리적 간격

SLM 물리 픽셀 수와 계산 N은 별개다. GUI의 기본 Fresnel SLM 예제는 **계산 N=512, 입력 FOV=6 mm**다.
720 nm, f=200 mm의 해당 Fourier 면은 N=512를 유지하면서 **dx=24 µm, FOV=12.288 mm**가 된다.
이는 N을 고정하고 출력 간격을 입력과 같게 유지한 계산이 아니다.

정상 입사에서 N=512, 입력 dx=8 µm를 예시로 설정하면 출력 dx=35.15625 µm, FOV=18 mm다.
이 예시의 8 µm는 실제 장비 사양으로 확정한 값이 아니다.
전역 Grid로 실제 LCOS 픽셀을 표현하려면 기존 4 samples/pixel 조건을 여전히 만족해야 한다.

Fresnel 모드는 ASM 전달함수를 사용하지 않으므로 이 경로에서 ASM bandlimit 오류가 발생하지 않는다.
그러나 임의의 격자와 phase map이 항상 정확한 것은 아니다. 이차 위상이 조명 영역에서
undersampled이거나 입사 Gaussian이 계산 창에서 잘리면 명시적으로 계산을 거부한다.
작은 B의 근접 결상면은 특히 더 촘촘한 격자나 다른 전파 알고리즘이 필요할 수 있다.

## 3. 생략한 aperture와 유지한 물리

이번 Fresnel 모드에서 생략한 것:

- 렌즈의 유한 pupil clipping.
- 시료/검출기 유한 면적에 의한 차단 및 검출 면적 적분.
- spatial filter/pinhole의 차수 차단.

계속 유지한 것:

- SLM의 입력 phase map, carrier, 경사 입사 투영과 반사 parity.
- SLM active area 및 설정된 pixel pitch/fill factor/phase quantization/잔류 반사 모델.
- splitter와 mirror/sample의 반사·투과 계수.
- 기존 ray route와 누적 길이 제한, 레이저에서의 경로 종단.

Fresnel에서 `Collected`는 이상적인 전면 검출 파워다. 실제 카메라 면적 적분값이 아니다.
기본 SLM 예제는 pinhole을 우회하므로 sample incident 약 4.05 mW, return 약 1.62 mW가 된다.
기존 ASM의 약 3.9997 mW/1.5999 mW와는 조건이 다르다.
Fresnel 화면에서는 유한 pinhole 차단을 가정하는 0/+1 ray guide를 숨긴다.
보드의 q 경로와 radius graph는 여전히 기준 경로이며 실제 회절 강도의 외곽선이 아니다.

## 4. GUI 사용법

1. `Load 720 nm SLM 4f`를 누르거나 `examples/slm_fresnel_720nm.json`을 연다.
2. SLM에서 flat/blaze/lens/vortex/custom 위상을 설정한다. Custom 입력은 기존 JSON의
   `slmPhaseMap` 또는 grayscale image import를 사용한다. 현재 import 제한은 최대 256×256이며,
   기본 계산 N=512가 512×512 물리 phase map 지원을 뜻하지 않는다.
3. Fourier 면 또는 Screen/Sample/Probe를 클릭하고 **계산하기**를 누른다.
4. `2D display`의 Intensity/Phase를 바꾼다. 재계산 없이 같은 복소 광장의 캐시된 보기를 표시한다.
5. Phase는 −π..π의 cyclic 색상 범례를 사용한다. I/Ipeak<1e-6에서는 위상을 어둡게 표시한다.
   이는 낮은 강도에서 위상을 물리적으로 의미 있게 해석하지 않도록 하는 표시 기준이다.
6. 설정을 수정하면 재계산 필요를 표시한다. 계산은 worker 하나로만 실행하며 취소할 수 있다.

기존 aperture/filter 검증은 Propagation=ASM, Grid=2048/FOV=6 mm로 선택할 수 있다.
모델은 JSON의 `wavePropagation: "fresnel"` 또는 `"asm"`으로 저장한다.
이 키가 없는 기존 JSON은 ASM으로 열어 이전 의미를 유지한다.
GS는 선택적인 별도 benchmark에만 남아 있으며 어떤 forward 계산 경로에서도 호출하지 않는다.

## 5. 독립 정량 검증

복소 광장 상대 오차는 전체 piston을 정렬한 뒤 `||E_test - c*E_reference||₂ / ||E_reference||₂`로 비교한다.
c는 단위 크기의 전역 위상이며 amplitude를 재정규화하지 않는다. 파워는 별도로 비교했다.

| 검사 | 결과 | 허용 오차 | 판정 |
|---|---:|---:|---|
| 단일 자유 전파 vs 별도 Fresnel 직접 적분 | 복소 상대 오차 4.2273e-15 | 1e-12 | 통과 |
| 두 Fresnel 전파 + 실제 lens phase vs Fourier | 복소 상대 오차 1.1999e-15 | 2e-12 | 통과 |
| Gaussian Fourier intensity 이론값 | NRMSE 2.3053e-8 | 2e-7 | 통과 |
| 임의 custom phase의 전체 bench Fourier 계산 | 복소 상대 오차 3.4941e-16 | 1e-12 | 통과 |
| defocus Fresnel chirp | 복소 상대 오차 5.2110e-16 | 1e-12 | 통과 |
| 렌즈 직후 입력의 후초점면 이차 위상 | 복소 상대 오차 9.2674e-17 | 1e-12 | 통과 |
| unequal 4f, 배율 −0.5의 복소 결상 | 상대 오차 0 | 1e-12 | 통과 |
| 반사 LCOS carrier의 Fourier 중심 위치 | −1.1292973172 mm, 절대 오차 2.2204e-16 mm | 약 1e-9 mm | 통과 |
| 순수 phase vortex의 중심/peak intensity 비 | 1.5362e-7 | ≤1e-5 | 통과 |

직접 적분은 FFT 함수를 호출하지 않는 별도 separable Fresnel kernel 행렬곱과 비교했다.
두 단계 검사에서는 각 자유 전파를 각각 평가하고 실제 렌즈 위상을 곱해 한 번의 이상 Fourier
변환과 비교했다. 따라서 Fourier 관계를 행렬로 선언만 하고 검사한 것은 아니다.
이 작은 오차들은 동일한 이상적 근축 모델의 수치적 관계를 검증한 결과이며, 실험 일치도나
임의 고주파 phase map의 연속 광학계 수렴을 입증하는 값은 아니다.

## 6. 레이저 뒤로 빔이 진행하던 문제

기존 `simulate()`는 laser를 모든 교차 탐색에서 제외했다. 이 때문에 빛이 laser에 돌아와도
그 뒤의 테이블 경계나 Screen까지 진행했다. 차수 guide도 같은 제외 조건을 갖고 있었다.

수정 후에는 발광면 위치의 유한 선분(기본 diameterMm=25.4 mm)에 도달한 ray를 흡수 종단한다.
처음 방출되는 ray는 시작점의 거리 0 교차를 제외하므로 정상 출발한다.
자기 source와 다른 laser 모두 양쪽에서 불투명하게 취급하고, 빗겨 가는 ray는 막지 않는다.
상세 3D housing이나 레이저 내부 되먹임은 계산하지 않는다.
Fresnel도 동일한 종료된 ray route를 사용하므로 흡수 종단 뒤에 wave Screen reading이 생기지 않는다.

검증한 항목:

- mirror에서 돌아온 빔: source에서 종료, 왕복 800 mm, 뒤 Screen hit 0.
- 10 mW ray reference power가 source 종단 기록에 남고 이후 segment 0.
- 다른 laser의 차단과, 그 laser를 빗겨 가는 빔의 정상 통과.
- 반사 SLM의 m=0/m=1 guide도 laser에서 blocked 처리.
- SLM 기본 배치의 stray branch가 laser에서 끝나며 후속 segment 0.
- GUI의 laser absorption marker와 footer의 stopped-at-laser 표시.

`TraceResult.laser_absorptions`의 power는 q/ray 기준 power이며 wave field 적분값으로 주장하지 않는다.

## 7. 개발 중 실패와 수정

- 초기 직접 Fresnel 검사 두 개는 거친 격자에서 output chirp 샘플링 검사가 거부했다.
  직접 적분 검사는 N=128/FOV=8 mm, 두 단계 초점 검사는 N=512의 자연 격자로 변경했다.
  허용 오차나 sampling guard를 완화하지 않았다.
- 첫 전체 실행은 86 passed/1 failed였다. 기존 GUI 핀홀 검사가 새 Fresnel 기본 모드에서
  ASM의 ROI 표시를 기대한 것이 원인이었다. 기존 검사는 ASM/N=2048을 명시하도록 고치고
  Fresnel GUI는 별도 검사했다. 해당 실패 로그는 `history/fresnel_initial_run/`에 보관했다.
- 레이저 종단을 적용하면서, laser를 왕복 공진기 축에 놓고 반복 통과시키던 과거 cap fixture는
  새 요구와 충돌했다. 외부 source와 splitter로 주입하는 공진기로 변경했다. SLM cap fixture는
  귀환광이 laser에 닿기 전에 누적 2500 mm 제한을 만나는 거리로 변경했다. 길이 제한은 유지했다.

최종 92개 검사는 수치 모델, 기존 ASM, 수동 계산/취소/캐시, Fresnel intensity/phase와 레이저 종단을
모두 포함한다. 각 측정값·오차·허용값은 [test_results.json](test_results.json), 요약은
[test_results.md](test_results.md)에 있다.

## 8. 빌드·화면·남은 범위

Linux x86_64, Python 3.13.5, Tk 8.6, NumPy 2.5.4, Pillow 12.3, PyInstaller 6.22.3에서 검증했다.
실행 파일: `/workspace/scratch/optic-wave-dist/OpticalBench`.
빌드 검증과 checksum은 [build_validation.json](build_validation.json), 로그는 [build_linux.log](build_linux.log)에 있다.

- [실행 파일의 Fourier intensity](screenshots/packaged-fresnel-intensity.png)
- [실행 파일의 Fourier phase](screenshots/packaged-fresnel-phase.png)
- [Vortex intensity](screenshots/fresnel-vortex-intensity.png)
- [Vortex phase](screenshots/fresnel-vortex-phase.png)

변경 소스는 `fresnel_optics.py`, `wave_optics.py`, `wave_view.py`, `optics.py`, `slm_geometry.py`, `app.py`다.
새 검사는 `tests/test_fresnel.py`, `tests/test_laser_stop.py`이며, 기존 테스트의 물리 비교는 유지했다.

이번 단계에서 보류한 것은 렌즈/시료/검출기 clipping과 pinhole의 Fresnel 통합이다.
실제 LCOS 픽셀/LUT/편광 보정, 고 NA/정밀 tilted-plane 전파, branch 간 간섭, 큰 임의 phase map의
독립 N/FOV 수렴 및 근접 결상면의 적응형 sampling도 다음 단계다. Fresnel approximation을
exact ASM/Maxwell 해석과 동일시하지 않는다.
