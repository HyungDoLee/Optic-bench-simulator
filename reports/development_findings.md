# Findings and correction history

## Confirmed pre-existing defects, fixed

1. **Strict path boundary:** a screen 2500.0000005 mm from a 720 nm laser was
   detected, and a segment exceeded the cap by 5e-7 mm (0.5 nm). The cause was
   intersection selection allowing `distance <= limit + EPS`. It now requires
   `distance <= limit`; a screen exactly at 2500 mm is still measured, but one
   even 0.5 nm beyond is not. Boundary and reflected-return cutoff tests cover it.
2. **Reflected-branch radius graph:** the graph filtered only the selected branch
   ID, omitting all pre-split source segments. Parent IDs and split distances are
   now recorded; `branch_segments` reconstructs the shared ancestry. Intermediate
   sample/probe graphs stop at the selected reading, not at later propagation.
3. **Scene validation:** JSON could accept negative aperture, out-of-range
   reflectivity, empty IDs and invalid hole spacing. Relevant inputs are now
   rejected; old valid scenes retain their behavior.

## Development test failures, diagnosed and corrected

The first new test run used the incorrect test-fixture ID `lens` rather than
`lens-1`, raising StopIteration. Corrected the fixture reference.

The first full GUI run then had 26 passed / 1 failed / 0 skipped. The failure
expected a 10 mm axial shift of L1 to change the sample radius by more than
0.0001 mm. Independent matrix multiplication gives
M=[[-0.5,-5 mm],[-0.0005/mm,-2.005]], q=71.2224062478+i252.6531644284 mm,
w=0.250010504760 mm. The radius change is only 0.000010504760 mm; the large
wavefront-curvature change is a better alignment diagnostic. The simulation
was correct. Replaced the unjustified radius threshold with quantitative checks
against this independent perturbed-geometry solution and detection of nonzero
Re(q). The failed full-run log and measurements are retained under `history/`.

Finally placed the return detector at the true sample conjugate plane by moving
the splitter to x=350 mm and detector to (350,350) mm. This removes the prior
350 mm detector defocus: final detector waist is 0.5 mm, path 1350 mm. Both the
input/sample relay and return detector are now explicit conjugate planes.

## Unresolved and external limitations

- Thorlabs official catalog requests failed at the proxy CONNECT step with 403.
  Hardware candidates in `docs/4f_design.md` remain unverified. Allowed-domain
  changes were saved as a draft, not applied or published by the agent.
- Sample response is a uniform scalar specular reflectivity. No roughness,
  spatial phase, interference, diffraction, polarization or objective NA model.
- The Screen/probe signal is ideal incident beam power, not finite detector-area
  integration. Optical losses other than splitter/sample R are assumed zero.
- No Windows EXE build or physical optical-bench measurements were performed.
- Coplanar/overlapping component surfaces are not supported: the tracer selects
  one nearest surface, then skips zero-distance intersections. Keep virtual
  probes at distinct locations, as in the supplied preset.
- Resolved 2026-11-09: source surfaces now terminate returning rays and order
  guides. See `fresnel_forward_validation.md` for regression evidence. Detailed
  source feedback physics and rejected-port hardware remain separate work.
