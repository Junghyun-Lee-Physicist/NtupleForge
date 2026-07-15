# Faithfulness audit — TopCPVCategorizer (NanoAOD) vs MiniAOD `SSBAnalyzer`

Does the NanoAOD `TopCPVCategorizer` (and, by extension, the NtupleForge
`topCPVCategorizer` module that ports it) faithfully reproduce the MiniAOD
generator logic recorded in [`03_miniaod_origin.md`](03_miniaod_origin.md)?

**Verdict in one line.** The **channel classification numerics are reproduced
faithfully** (same codes, same all-hadronic=0 convention), but the port (1) drops
the original's malformed-selection diagnostic, (2) forces the background channel
to 0 where the original computed it, (3) anchors the family tree on the *last
copy* top rather than the *hard-process* top, and (4–6) re-implements the
W⁻-daughter / τ-resolution / ghost-B steps with NanoAOD-native inputs that are
equivalent in intent but not identical in mechanism.

Legend: ✅ faithful · ⚠️ divergent (document it) · ⬆️ improved on a known origin wart.

---

## 1. ⚠️ Channel failure handling — **the `-999` question**

| | MiniAOD origin | NanoAOD TopCPV |
|---|---|---|
| `Channel_Idx` base | `0`, then `+=|pdg|` per lepton in `SelectedPar` | `0`, then `+=|pdg|` per lepton in slots 8–11 |
| all-hadronic | `0` | `0` |
| **malformed selection** | `0` **and prints `"SelectedPar Error"`** | `0`, **silent** |
| sentinel `-999`? | **never** | never |

**Finding.** The MiniAOD code does **not** use `-999`. On an incomplete 12-slot
build it prints `SelectedPar Error` (`03_miniaod_origin.md` §1.4) and then writes
`Channel_Idx = 0` anyway (§2.1). So folding failures into `0` is the **original,
intended behavior** — `Channel_Idx == 0` legitimately means "all-hadronic **or**
unclassifiable", and the *only* signal separating the two is the printed error.

TopCPV reproduces the `0` numerics exactly but **dropped the `SelectedPar Error`
print** — it is fully silent on malformed selections. That is the one real
regression here.

**Therefore, for decision ②:** moving `Channel_Idx` to `-999` on failure would
**diverge from the source of truth**, not match it. The faithful choice is to keep
`Channel_Idx == 0` bit-for-bit and **expose "unclassifiable" beside it** in a
second integer field, `Channel_Idx_Expanded`:

- `Channel_Idx` — bit-identical to MiniAOD (`0` = all-hadronic **or** unclassifiable).
- `Channel_Idx_Expanded` — equal to `Channel_Idx` for a well-formed selection,
  but a sentinel (`-999`) when `isSignal` is true and the 12-slot build is
  incomplete (any of slots 2–11 `< 0`, the NanoAOD analogue of MiniAOD's
  `SelectedPar.size() != 12`). So genuine all-hadronic stays `0`, unclassifiable
  becomes `-999`, and everything else is unchanged.

This restores, in modern form, the diagnostic the origin had (its
`cerr << "SelectedPar Error"`) **without touching the faithful `Channel_Idx`**, and
is paired with an end-of-job counter naming the unclassifiable rate.

> Port rule adopted: `Channel_Idx` stays numerically identical to the origin;
> "unclassifiable" lives **only** in `Channel_Idx_Expanded`, never inside
> `Channel_Idx`.

---

## 2. ⚠️ Background channel index

- **MiniAOD:** the §2.1 lepton loop runs over the background `SelectedPar` as
  well, so a background event with a leptonic boson decay gets a **non-zero**
  `Channel_Idx` (`03_miniaod_origin.md` Note D).
- **TopCPV:** `ComputeChannelDirect()` does `if (!isSignal) { channel_idx = 0; return; }`
  — background is **forced to 0**.

**Impact.** Irrelevant for ttbar signal samples (where `isSignal` is true for
~100% of events, so the categorizer's actual targets are unaffected) but **not
faithful** for non-ttbar samples.

**Restoration (and a correction).** It is *not* enough to delete the
`if(!isSignal) channel_idx = 0` line. `FillBackgroundSelection()` fills only the
variable-length `picked` list (→ the `GenPar_*` output vectors) and **never writes
`selectedIdx[8..11]`** — those stay `-1` from `ClearState()`. `ComputeChannelDirect()`
reads only slots 8–11, so a background event yields `0` *with or without* the
forced line. To match MiniAOD, the channel lepton sum must iterate the **full
selected-particle list** (signal: the 12 slots — equivalently 8–11, since only
those hold leptons; background: the `picked` list), exactly as MiniAOD loops the
whole `SelectedPar`. The NtupleForge module implements `ComputeChannelDirect()`
this way from the start, so background channels are recovered faithfully.


### 2b. ✅ Background *selection construction* (2026-07-02 re-audit — **RESOLVED 2026-07-10**)

§2 restored the channel **sum** to run over the full selected list, but the
re-audit finds the selected list itself is built differently from MiniAOD on the
background branch:

| | MiniAOD (`03_miniaod_origin.md` §1.6) | module / standalone (`FillBackgroundSelection`) |
|---|---|---|
| base set | beam protons (idx 0,1) + **every status 21–23 particle** (the whole hard process, incl. non-boson partons) | **last-copy bosons only** (`|pdg| ∈ {6,23,24,25}`) |
| decay products | status-1/2 leptons whose **direct mother is a boson** (moved from `FinalPar`) | recursive off-flavour descendants of each picked particle |
| τ rescue | none needed (status-23 τ is in the base set) | extra loop appends `fromHardProcess && isLastCopy` τ not already picked |

Consequences to check on real files (channel arithmetic itself is ✅ §2):

1. **Explicit-Z `Z→ττ` may double-count.** The recursion picks the τ **first
   copy** (daughter of Z), the rescue loop then also appends the τ **last copy**
   (it carries `fromHardProcess`+`isLastCopy` and is not in `picked`) →
   `Channel_Idx = −60` where MiniAOD gives `−30`. Discriminator on any DY
   output: `Events->Draw("TopCPVCat_Channel_Idx","TopCPVCat_isSignal==0&&TopCPVCat_Channel_Idx<-20")`
   — a peak at −60 confirms the double count; −30 refutes it (i.e. NanoAOD
   pruning dropped one of the two copies).
2. **Boson-less ME records lose e/μ channels.** If a sample's `GenPart` has no
   explicit boson row (ME-level ℓℓ with parton mothers), the rescue loop is
   **τ-only**, so `e/μ` are never picked → `Channel_Idx = 0` where MiniAOD
   (which takes all status-21–23 particles) gives ±22/±26. Discriminator:
   fraction of DY events at `Channel_Idx ∈ {22,26}` vs `0`.
3. **Background `GenPar_*` rows differ regardless** — MiniAOD records the whole
   hard process (+ protons); the module records bosons + their decays only.
   Channel-neutral, but any consumer of background `GenPar` rows must know.

**Status — RESOLVED 2026-07-10.** The faithful rebuild is applied to **both**
codebases (module + standalone v1.8; see `../03_DECISIONS.md` →
D-2026-07-10-background-hardprocess): base set = every `isHardProcess` particle
(NanoAOD equivalent of MiniAOD's status-21–23 `TreePar`, hadronizer-independent)
+ status-1/2 leptons with a **direct** boson mother, both in ascending index;
the recursion and the τ-rescue loop are gone. Beam protons remain unrecoverable
(no rows; cf. §8). Both risks are now regression-tested on synthetic events —
explicit-Z Z→ττ gives −30 (not −60) and boson-less ME μμ gives 26 (not 0) — in
`script/test_reader_lifecycle.py` (Python) and the standalone's
`validation/crosscheck/` harness (C++), which assert **identical values from
both implementations**. The two `Draw` checks above stay useful as a one-time
sanity pass on the real DY production after the standalone is rebuilt on lxplus.

---

## 3. ⚠️ Which top copy anchors the family tree

| Quantity | MiniAOD | TopCPV | Match? |
|---|---|---|---|
| `GenTop`/`GenAnTop` kinematics | `status == 62` (post-FSR, decaying top) | `isLastCopy` top | ✅ effectively the same particle |
| `GenPar` slot 2/3 (`t`/`t̄`) anchor | `status 21–23` **hard-process** top | `isLastCopy` top | ⚠️ different copy |

**Finding.** In MiniAOD the dedicated `GenTop` branch and the family-tree `t`
slot are *different copies* of the top (status-62 vs status-22); TopCPV makes both
the **last copy**, which is internally consistent and physically the decay-time
top. Consequence:

- `GenTop_*`/`GenAnTop_*` agree with MiniAOD (both ≈ the decaying top). ✅
- `GenPar` slot 2/3 `pt/eta/phi/mass/energy/Status` **differ** from MiniAOD by the
  hard-process→last-copy FSR difference. ⚠️

Minor (2026-07-02): for **background** events MiniAOD leaves the `GenTop`
vector branches empty (no status-62 top), while the module writes scalar
sentinels (−999). Shape/type cosmetic only; module ≡ standalone.

For the CPV triple products, take the top/antitop 4-vectors from the dedicated
`GenTop`/`GenAnTop` branches (faithful), **not** from the `GenPar` slots (which
diverge by construction). The simplification is the intended NanoAOD design
(`docs/TECHNICAL.md` §2.1 in the TopCPV package: `isLastCopy` replaces the
hard-process tag).

---

## 4. ⬆️ W⁻ daughter selection

- **MiniAOD:** W⁺ daughters via an explicit `IndexLinker` descendant test (take
  two); W⁻ daughters are **leftover** `TreePar` entries — the guard is commented
  out (`03_miniaod_origin.md` Note B).
- **TopCPV:** `WDaughters(Wm_idx)` resolves W⁻ daughters explicitly from the
  daughter map (excluding W radiation copies), symmetric with W⁺.

**Finding.** Same result for clean events; TopCPV **removes a fragile "leftovers"
assumption**. Improvement, not a regression — but it means the two can disagree on
pathological events where stray `TreePar` entries survived in MiniAOD.

---

## 5. ⚠️ Final channel (τ → ℓ) mechanism

- **MiniAOD:** walks each selected `τ` to its leptonic daughter through the
  gen-daughter map (`IndexLinker` over `SelParDau`/`FinalPar`) and rewrites
  `Channel_Idx_Final` (`03_miniaod_origin.md` §2.2).
- **TopCPV:** counts `e/μ` in `GenDressedLepton` and uses
  `GenDressedLepton_hasTauAnc` to populate `Channel_Tau_Lepton`.

**Finding.** Same physics question ("what leptons does the detector see after τ
decay?"), **different inputs**. `GenDressedLepton` is FSR-dressed and carries an
implicit acceptance/`pt` floor, so rare edge cases (very soft τ-daughter leptons,
dressing differences) can shift `Channel_Idx_Final` relative to the MiniAOD
gen-tree walk. Equivalent in the bulk; not guaranteed bit-identical.

**Verified line-level (2026-07-02 re-audit).** The module's daughter-map walk was
checked statement-by-statement against §2.2 of the origin: map iteration in
ascending τ index (`sorted` ≡ `std::map` key order), per-τ descendant order =
`FinalPar` order = ascending GenPart index, push-before-pdg-check (intermediate
same-pdg τ copies enter the selected set but neither fill GenPar nor touch the
channel), τ removal triggered by the **first** non-same-pdg descendant
*including neutrinos* (`Lepton_Mom_flag`), and the `<14`/`>14` sign rules for
mother and daughter — all identical, so `Channel_Idx_Final`,
`Channel_Lepton_Count_Final`, and the τ-daughter GenPar appends are
order-exact. Also re-verified: the §2.1 τ-descendant collection is equivalent —
MiniAOD's `FinalPar` had the τ itself (and its W-sibling ν) already erased,
which the module reproduces by excluding the walk's start and by ν-siblings
being unreachable from the τ.

**Restoration.** This is recoverable and matters most for CPV (the τ-veto depends
on it). NanoAOD keeps τ decay products in `GenPart` (tagged by
`statusFlags` bit 4 `isDirectTauDecayProduct`), so the module reproduces MiniAOD by
walking each selected τ to its leptonic daughter through the **same daughter map**
it already builds — no `pt` floor, every τ→ℓ resolved — instead of relying on
`GenDressedLepton`. `Channel_Visible_Tau` (from `nGenVisTau`) is kept as a
**NanoAOD bonus** the MiniAOD code did not track.

---

## 6. ⚠️ Ghost-B matching (corrected)

- **MiniAOD:** consumes the dedicated `matchGenBHadron` products
  (`genBHadIndex`, `genBHadJetIndex`, `genBHadFromTopWeakDecay`, `genBHadFlavour`)
  — the official ghost-reclustering result. `FromTopWeakDecay`/`Flavour` are read
  straight from those collections.
- **TopCPV:** takes `GenJet_hadronFlavour == 5` jets, matches the **nearest
  last-copy b-quark** within `ΔR ≤ 0.4`, and derives `FromTopWeakDecay` by walking
  the b-quark's mother chain for a top ancestor.

**Finding — split by output, because the two halves differ in fidelity:**

- **`GenBJet` (the jet side) — ✅ already faithful.** NanoAOD's
  `GenJet_hadronFlavour` is produced by the **same ghost B-hadron clustering**
  CMSSW module the MiniAOD path used. So "`hadronFlavour == 5` gen-jets" *is*
  the set of jets MiniAOD tagged via `genBHadJetIndex` — same jets, same
  kinematics. No fidelity loss. (My earlier audit over-flagged this.)
- **`GenBHad` (the hadron side) — ⚠️ best-effort.** MiniAOD stores the **B-hadron**
  4-momentum; NanoAOD pruning usually drops the B-hadron and keeps the **b-quark**,
  so TopCPV stores the nearest b-quark instead. Same top, but hadron ≠ quark
  kinematics (`pt` etc. differ). Not recoverable from standard NanoAOD.
- **`GenBHad_FromTopWeakDecay` — ⚠️ recomputed.** MiniAOD reads the official flag;
  TopCPV rederives it by mother-chain ancestry. Agrees in the bulk, can differ
  from the official logic at edge cases. Not recoverable (the official collection
  is absent from NanoAOD).

So the **truth-labelling that matters** (which gen-jet is the b from t→bW) is
faithful via `GenBJet`; only the B-hadron's own kinematics and the official
`FromTopWeakDecay` flag are approximations, and they cannot be restored without a
MiniAOD friend tree (`docs/TECHNICAL.md` §8 in the TopCPV package).

---

## 7. ⚠️ Lost / bonus branches

| Branch | Status |
|---|---|
| `GenJet_HCalEnergy`, `GenJet_ECalEnergy` | ⚠️ **lost** — `hadEnergy()`/`emEnergy()` have no NanoAOD equivalent |
| `Frag_*_Weight`, `Semilep_Br*_Weight` (B-frag) | ⚠️ **lost** — not in NanoAOD; `PSWeight[0..3]` is an *approximate* ISR/FSR proxy, or recover via friend tree (`docs/TECHNICAL.md` §8) |
| `Channel_Visible_Tau` (`nGenVisTau`) | ⬆️ **bonus** — not in MiniAOD |

---

## 8. ✅ Faithful as-is

- `Channel_Jets` / `Channel_Jets_Abs` quark-pair encoding (`10*p1+p2`, the
  `%2 == WIndex` up-type rule, the `Abs` digit-sort normalization) — reproduced
  verbatim.
- τ sign convention (`Channel_Idx -= |pdg|` for τ) — reproduced.
- `GenMET_pt`/`GenMET_phi` — same quantity.
- 12-slot layout and the `Mom*/Dau*` wiring table — reproduced **for slots
  4–11**. ⚠️ Slots 0/1 and the t/t̄ mother fields necessarily differ
  (2026-07-02 re-audit): MiniAOD writes the **real beam protons** (GenPart
  indices 0,1 — pdg 2212, true kinematics, `Dau=(t,t̄)`, `nDa=2`) and gives
  t/t̄ `Mom1=0, Mom2=1, nMo=2`; NanoAOD **prunes beam protons**, so the
  module/standalone write `-1`/placeholder rows (pdgId 0, kin −999) and t/t̄
  get `Mom1=Mom2=−1, nMo=0`. Unrecoverable; channel-neutral (pdg 0/2212 are
  not leptons); module ≡ standalone.
- MC-only, fail-fast on missing `GenPart` — matches the spirit of the original
  (which only ran the block under `!isData`).

---

## 9. Net assessment & final port directive

TopCPV *was* a faithful reproduction of the MiniAOD channel classification with
documented NanoAOD simplifications. **As of 2026-06-28 the reference is fixed as
the MiniAOD `SSBAnalyzer`, and the restorations below are applied to BOTH the
standalone TopCPV and the NtupleForge module** (see `../03_DECISIONS.md` →
D-2026-06-28-miniaod-reference), so the two now track MiniAOD and each other.

**Restored in both codebases (now matching MiniAOD):**

1. **Malformed-selection diagnostic (§1).** Add integer `Channel_Idx_Expanded`
   (`= Channel_Idx`, but `-999` when `isSignal` && any slot 2–11 `< 0`) plus an
   end-of-job counter. `Channel_Idx` itself stays bit-identical to MiniAOD.
2. **Background channel (§2).** Compute the channel lepton sum over the **full
   selected-particle list** (not just slots 8–11), so background events get their
   MiniAOD channel value instead of a forced `0`. (Note: this required iterating
   the full list, *not* merely deleting the forced-zero line — see §2.)
3. **τ → ℓ final channel (§5).** Resolve τ leptonic decays by **walking the
   GenPart daughter map** (as MiniAOD did), not via `GenDressedLepton`, removing
   the implicit `pt`/dressing threshold. *(Standalone: done in v1.8, 2026-07-10 —
   `GenDressedLepton` branches no longer read.)*
3b. **Background selection construction (§2b, 2026-07-10).** Base set =
   `isHardProcess` particles + direct-boson-mother status-1/2 leptons in both
   codebases, replacing the boson-recursion + τ-rescue heuristic.

**Keep as-is (TopCPV's choice is equal or better):**

4. **W⁻ daughters (§4)** — keep TopCPV's explicit `WDaughters` (more robust than
   MiniAOD's "leftovers").
5. **Top copy for `GenPar` slot 2/3 (§3)** — keep **last copy** (physically the
   decaying top). *Not* reverting to the hard-process copy. CPV top/antitop momenta
   come from the dedicated `GenTop`/`GenAnTop` branches (which already agree with
   MiniAOD), so the slot-kinematics difference is cosmetic.
6. **`GenBJet` (§6)** — already faithful (NanoAOD `GenJet_hadronFlavour` *is* the
   ghost-clustering result).

**Cannot restore (absent from standard NanoAOD):**

7. `GenBHad` hadron kinematics & official `GenBHad_FromTopWeakDecay` (§6),
   `GenJet_HCal/ECalEnergy`, and B-fragmentation weights (§7) — best-effort
   (b-quark proxy / mother-chain flag / `PSWeight` proxy) or via a MiniAOD friend
   tree only.

**Document so values are never mistaken** (§2 background semantics, §3 slot vs
`GenTop`, §5/§6 mechanism differences, §7 proxies).
