# 경사 입사 phase-only LCOS와 Fourier 차수 선택

2026-11-09: GUI의 SLM preset은 **Fresnel 이상 모드**로 시작한다. 렌즈/시료/검출기
clipping과 pinhole을 생략해 주어진 위상의 Fourier 변환을 먼저 확인한다.
아래의 필터 통과율과 차수 선택 설계는 기존 **ASM 유한 구경 모드**에 해당한다.
최신 구현과 검사 결과는 [Fresnel 보고서](../reports/fresnel_forward_validation.md)를 참고한다.

## 현재 설계

이 문서는 이전의 수직 입사·두 splitter 구성을 대체한다. LCOS 입출력 분리와
0차광 제거를 독립된 기능으로 구현했다. SLM은 반사형 phase-only이며 진폭을
프로그래밍하거나 vortex 중심 진폭을 인위적으로 깎지 않는다.

- **경로 분리:** LCOS에 5° 입사, 입사광과 거울반사광의 역진행 방향 사이 각도는 10°.
  LCOS 입출력 분리를 위한 splitter는 없다.
- **차수 분리:** target phase에 별도 carrier 2pi*u/period를 더한다. 기본 period는 128 µm.
- **차수 선택:** L1의 Fourier 면에서 +1 위치에 반경 0.2 mm의 이동 pinhole을 둔다.
- **시료 반사 분석:** 시료 근처의 splitter 한 개로 귀환광을 별도 f=50 mm 결상계로 꺾는다.
  이 splitter는 LCOS 경로 분리용이 아니다.

이는 720 nm와 작은 근축 빔을 위한 설계 시작점이다. 특정 제조사 LCOS가 5°에서
2pi stroke/위상 전용 응답을 보장한다는 뜻이 아니다. 해당 장비의 720 nm·입사각·
선형편광에 대한 LUT와 허용각을 확인하고 실제로 보정해야 한다.

## 실제 배치와 부품

| 요소 | X,Y [mm] | 법선각 | 기준 파라미터 |
|---|---|---|---|
| Laser | 약 704.558,547.906 | 진행각 10° | 720 nm, 10 mW; LCOS에서 w=0.5 mm |
| LCOS | 1000,600 | 5° | eta_mod=0.8, eta_residual=0.01 가정 |
| Lens 1 | 800,600 | 0° | f1=200 mm, Ø25.4 mm |
| Fourier filter | 600,600 | 0° | hole center=+1.129297 mm, radius=0.2 mm |
| Lens 2 | 500,600 | 0° | f2=100 mm, Ø25.4 mm |
| Sample pickoff | 450,600 | 45° | 50:50 NPBS |
| Sample | 400,600 | 0° | R=0.8 가정 |
| Collection lens | 450,550 | 90° | f=50 mm |
| Return camera | 450,450 | 90° | 1:1 sample image |
| Illumination dump | 450,850 | 90° | Sample pickoff 조명 누설 수집 |

LCOS->L1=200 mm, L1->L2=300 mm, L2->sample=100 mm다. 입력 beam은 L1 위치에서
반사축과 약 35.27 mm 떨어져 Ø25.4 mm lens를 피한다. 실제 holder 외경/높이도
확인해야 한다. 반사광은 왼쪽으로 진행하고 sample return은 pickoff를 거쳐 위로 간다.

Sample->collection lens는 folded distance 100 mm, lens->camera도 100 mm이므로
f=50 mm의 2f-2f, 배율 -1이다. B=0을 별도 검사한다. Source->LCOS 300 mm,
LCOS->sample 600 mm, sample->camera 200 mm로 검출 경로는 1100 mm다.

필요한 하드웨어는 720 nm LCOS/보정 가능한 선형편광, input steering mirrors,
200/100 mm NIR relay lenses, **400 µm precision pinhole + XY translation**,
sample pickoff NPBS, 50 mm collection lens, camera, dumps와 source isolation이다.
핀홀은 광축에서 약 1.13 mm 이동해야 한다. 일반 iris가 400 µm까지 닫히는지
확인하지 않고 대체해서는 안 된다. 렌즈 거리 기준은 실제 principal plane/EFL이다.
이 문서의 부품 치수와 반사계수는 카탈로그/실측으로 검증한 구매 명세가 아니다.

## 입사각과 carrier를 분리하는 계산

3D 벡터로 d_ref=d_in-2(d_in dot n)n을 계산한다. Carrier의 접선 단위벡터 g에 대해
outgoing tangential direction = incoming tangential direction + m*lambda/period*g,
normal component는 반사 반구에서 단위 길이가 되도록 정한다. 진행할 수 없는
차수는 evanescent로 표시한다. slm_geometry.py는 이 3D 벡터식을 제공하지만,
**bench의 비순차 교차 탐색과 GUI는 여전히 2D 공면 모델**이다. 전체 3D 장면이나
vector wave solver를 구현했다고 주장하지 않는다.

소각도에서 Delta theta≈lambda/(period*cos(theta_r))이고 focal separation≈f1*Delta theta다.
720 nm, 128 µm, 5°에서는 약 0.32360°, 1.12930 mm다. 정확한 grating direction과
paraxial Fourier 위치는 작은 고차 차이가 있으므로 각각의 모델로 검증한다.
붙여넣은 답변의 532 nm, 64 µm, 200 mm 예시는 **0°/0 mm가 아니라**
약 0.47627665°와 1.66255744 mm다.

실제 LCOS surface coordinate는 beam-normal coordinate/cos(incidence)로 투영한다.
위상/픽셀/개구는 surface 좌표에서 계산하고, 반사 후 local u parity를 반전한다.
이는 작은 각도·작은 NA의 projected scalar 근사다. Scheimpflug tilted-plane imaging,
vector polarization, 넓은 시야의 정밀한 tilted ASM는 아직 없다. 여기서 5°에 의한
0.5 mm footprint 내 axial variation은 약 0.044 mm로 입력 Rayleigh length 1090.8 mm에
비해 작다. 높은 NA나 넓은 target image로 일반화하려면 추가 검증이 필요하다.

## 실제 0차광 모델과 에너지 보존

이상적인 phase-only LCOS의 active pixel은 sqrt(eta_mod)*exp(i*phi)다. 현실의 잔류
무변조광을 보기 위해 고정된 coherent surface term sqrt(eta_residual)*exp(i*psi)를 더한다.
Dead space에는 별도의 고정 reflectivity를 설정할 수 있다. programmed control은 여전히
위상뿐이다. 표면항 간 간섭으로 생기는 진폭 변화는 물리적 imperfection 모델이다.

각 pixel에서 |r|<=1을 보장하기 위해 sqrt(eta_mod)+sqrt(eta_residual)<=1 및
sqrt(eta_dead)+sqrt(eta_residual)<=1을 요구한다. 합을 임의로 재정규화하지 않는다.
이 계수는 고립된 각 항의 power coefficient이며, coherent sum의 총 반사율과 같지 않다.
실제 LCOS multilayer/편광/LUT의 대체물이 아닌, 명시적인 phenomenological 모델이다.

기본값 eta_mod=0.8, eta_residual=0.01, phase=0, fill factor=1은 **검증용 가정**이다.
많은 carrier 주기를 포함하는 Gaussian에서 Fourier 면 power는 약 8.10 mW이고,
0 ROI는 약 0.099993 mW, +1 hole ROI는 약 7.999413 mW다. Tilt만 바꾸어도
unmodulated term은 specular focal origin에 남는지 따로 검사한다.

0차광과 원하는 광장은 서로 다른 Gaussian peak로 분리되고, 실제 field에 원형 pupil을
곱해 filtering한다. Sample incident는 약 3.99968 mW, detector는 약 1.59986 mW다.
Hole을 0차광으로 옮기면 detector가 약 0.02 mW로 변한다. 이 값은 실측 효율/소광비가 아니다.
Gaussian tails, 픽셀화, band limit, finite pupils에 따른 수치 오차를 보고서에 기록한다.
Target의 Fourier bandwidth가 넓어지면 400 µm hole이 원하는 광장도 자를 수 있으므로
필터 반경을 target에 맞게 다시 정해야 한다.

## GUI 사용

1. Load 720 nm SLM 4f를 누른다. incidence=5°, carrier=0.128 mm,
   Propagation=Fresnel, input Grid=512/FOV=6 mm다. 이 N은 실제 LCOS 픽셀 수가 아니다.
   legacy slm_blaze/slm_vortex JSON은 기존 ASM/Grid2048 설정을 유지한다.
2. LCOS Properties의 Preset incidence를 바꾸면 입력 source 위치/방향만 바꿔 output axis를
   유지하고, 연동된 Fourier hole 위치를 갱신한다. 이 preset은 렌즈 clearance 때문에
   |angle|=2..10°만 허용한다. 이는 제조사 보장 범위가 아니다.
3. Carrier period/sign은 target pattern(flat/lens/vortex/custom)과 독립적이다.
   Legacy blaze는 별도 carrier가 없을 때 slmPeriodMm을 사용하며 이중 carrier를 더하지 않는다.
4. Fourier filter를 클릭하고 **계산하기**를 누른다. Fresnel에서는 차단 전 광장을 보여준다.
   2D display를 Intensity/Phase로 전환하면 동일한 결과의 강도/위상을 볼 수 있다.
   Phase는 −π..π의 cyclic 색상이며 I/Ipeak<1e-6은 어둡게 표시한다. 전체 piston은 기준에서 제외한다.
   ASM으로 전환하고 Grid=2048/FOV=6 mm로 설정하면 incoming 0/+1 intensity,
   각 ROI power와 hole 윤곽을 확인할 수 있다. Filter offset/radius로 원하는 차수를 선택한다.
   화면 표시 crop은 계산장/출력을 바꾸지 않는다.
5. ASM의 0차 guide는 amber/dashed, +1 guide는 green이다. 이들은 carrier 방향 진단용이며
   회절 효율 예측이나 full field를 대신하지 않는다. 0 guide는 filter에서 종료한다.
   q 경로는 filter/위상에 영향받지 않는 기준 축이다. Fresnel에서는 유한 pinhole에
   따른 차수 차단 guide를 숨기고 q 경로만 기준으로 표시한다.
6. Input shape/phase와 실제 0차 항은 Scalar wave mode에서만 계산된다. 각 측정면에서
   **계산하기**를 눌러 downstream Sample/Camera의 power를 확인한다.
   Fresnel은 pinhole을 우회하므로 ASM과 전달 파워가 다르다.
7. Wave 계산은 선택된 장면의 복사본으로 한 번만 실행한다. UI 조작은 계속 가능하고
   **취소**는 현재 전파 연산이 끝난 뒤 적용된다. 모드 선택·드래그·창 크기 변경으로
   FFT를 실행하지 않는다. 결과는 고정된 미리보기로 유지하고, 설정/측정면/Grid가 바뀌면
   이전 결과의 측정면과 **재계산 필요**를 표시한다. 새 결과는 버튼으로 갱신한다.
   긴 수치 readout은 분석 패널의 스크롤바로 볼 수 있다.
8. 실제 광장의 centroid, 2σ 반경, 평균 local 방향을 readout에 표시한다.
   평균 횡방향 파수와 법선에 대한 평균 입사각도 각 도착면의 계산 데이터에 기록한다.
   0/+1이 공존하는 면의 평균 방향은 +1 chief ray와 같지 않다. 필터 이후 선택 차수의
   방향과 guide를 비교한다. q 경로는 계속 기준 축이며 광장 중심 경로로 바꾸지 않는다.

waveGrid와 wavePropagation은 JSON에 저장한다. 모델 키가 없는 예전 scene은 ASM으로 연다.
기존 slm_blaze_720nm.json/slm_vortex_720nm.json은 새 경사 입사 배치로 갱신했다.
Old two-splitter 및 amplitude-core 화면은 현행 설계의 근거가 아니다.

## 검증 및 제한

기존 검사를 유지하고 test_offaxis.py에 incidence/3D direction/carrier/filter 검증을 추가했다.
최종 수치·GUI 결과는 reports/test_results.md와 JSON을 참고한다. 실제 장비 실측 비교는 0건이다.
픽셀 pitch·조사 빔 크기·GS와 핀홀에 관한 후속 평가는
[재평가 대응 보고서](../reports/review_v53b91f6_response.md)와
[국소 GS 검증](../reports/hologram_validation.md)을 참고한다. 512×512, 8 µm 예시는
실제 보유 장비 사양이 아니다. 국소 pixel-array Fourier 모델은 전체 bench ASM과 별개이며,
기존 pixel-resolved 모드의 4 samples/pixel 제한을 완화하지 않는다.

전체 bench는 공면, wave는 local projected scalar 모델이다. 고 NA/tilted-plane 재구성,
full Jones/LCOS response, RCWA, 실제 gray-voltage LUT, source isolator/beam dump의 열설계는
미구현이다. 순수 vortex의 긴 회절 꼬리나 실제 pixel-gap의 높은 차수는 현 FFT 창에서
거부될 수 있다. 그 경우 sampling/energy 검사를 끄거나 amplitude core를 넣지 않는다.
선택된 carrier의 +1 guide와 실제 ROI power를 구분하며, 모든 산란 차수를 새 branch로
탐색하거나 coherent하게 합치지는 않는다. 돌아오는 미검출 포트는 실험에서 반드시
분석/차단해야 하며 이 구성만으로 완전한 source isolation을 달성했다고 해석하면 안 된다.

레이저는 돌아온 빔에 대해 불투명한 종단이다. 발광면 위치의 유한 선분(기본 Ø25.4 mm,
JSON diameterMm으로 변경 가능)에 다시 닿으면 해당 ray/차수 guide를 중단한다.
이상적인 Fresnel 모드에서도 이 경로 종단은 적용한다. 되먹임이 레이저의 동작을 바꾸는
효과나 케이싱의 상세 3D 형상은 모델링하지 않는다.
