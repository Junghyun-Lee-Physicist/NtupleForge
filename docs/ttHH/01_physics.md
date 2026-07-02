# Physics Basis

The physics motivation behind NtupleForge's analysis target and the tt+jets
categorization scheme. This is the "why"; the implementation ("how") is in
[`02_legacy_ttbar_pipeline.md`](02_legacy_ttbar_pipeline.md).

---

## 1. Analysis target

**ttHH → 4b, fully hadronic channel, Run-2 2017 UL, NanoAODv9.** The final
state is two top quarks plus two Higgs bosons, with both Higgs decaying to
b-quark pairs (H→bb), giving a b-rich, high-jet-multiplicity hadronic event.
The experimental challenge is the very large, heavy-flavour-rich background
from tt+jets, so understanding the heavy-flavour content of the background
precisely is central to the measurement.

References: **ttHH AN-2022/122** (the analysis note this work follows) and
**ttH AN-19-094** (earlier reference using the same gen-categorization chain).

---

## 2. Why categorize tt+jets

The dominant background is tt+jets, and what matters is the **heavy-flavour
content of jets that do *not* come from the top-quark decay** (`t → Wb`).
Throughout, **"additional"** means *not from the top decay chain*.

The problem with inclusive samples: standard 5-flavour-scheme (5FS) ttbar
samples (`TTToHadronic`, `TTToSemiLeptonic`, `TTTo2L2Nu`) model additional
b-quarks through the **parton shower (PS)**. At the high jet multiplicities
that ttHH→4b selects, the PS modelling of extra b-quarks carries large
tune-dependent uncertainties — exactly in the region that matters most.

The cure: **sample stitching.** Keep only the light-flavour and cc events
from the inclusive 5FS sample, and take all b-jet topologies from a dedicated
**4-flavour-scheme (4FS)** sample (`TTbb_4f`) that generates the additional
b-quarks at **matrix-element level** (better-controlled than the shower). To
combine the two samples without double-counting, every event must be assigned
a category, so the stitching cut can be applied **per category** rather than
per sample. The same per-event label feeds per-category systematic
uncertainties (e.g. the 50% normalization prior on `tt+2b`).

This per-event labelling is what the categorizer produced. In the **current**
NtupleForge direction the labelling is done downstream in the analyzer
instead, but the physics below is unchanged and defines what that analyzer
must compute.

---

## 3. The categorization tool chain

The official CMS tool is the **GenHFHadronMatcher → GenTtbarCategorizer**
plugin chain. It ghost-clusters generator-level B/C hadrons into the
gen-jet collection, identifies which heavy-flavour jets are additional, and
packs the result into a single integer, **`genTtbarId`**, stored in NanoAOD.
This is the AN-cited categorizer and the authoritative source of truth.

Anchor references (prefer these over any prose summary):

- **`GenTtbarCategorizer.cc`** (CMSSW `TopQuarkAnalysis/TopTools/plugins/`),
  lines ~282–300 — the definitive `genTtbarId` integer encoding.
  <https://github.com/cms-sw/cmssw/blob/master/TopQuarkAnalysis/TopTools/plugins/GenTtbarCategorizer.cc>
- **GenHFHadronMatcher TWiki** — the ghost-clustering procedure.
  <https://twiki.cern.ch/twiki/bin/view/CMSPublic/GenHFHadronMatcher>

### `genTtbarId` encoding (the part that defines categories)

The category is fully determined by `genTtbarId % 100`:

| `genTtbarId % 100` | Category | Meaning |
|--------------------|----------|---------|
| 0     | tt+LF | no additional heavy-flavour jets |
| 41–45 | tt+cc | additional c-jets (variants by c-hadron multiplicity) |
| 51    | tt+b  | 1 additional b-jet containing 1 b-hadron |
| 52    | tt+2b | 1 additional b-jet containing ≥2 b-hadrons (collinear g→bb) |
| 53–55 | tt+bb | ≥2 additional b-jets (variants by hadron multiplicity) |

The leading three digits (b-jets from top, b-jets from W, c-jets from W) are
information-only for this scheme — the category is the modulo-100 part.

---

## 4. The five categories

Acceptance for additional jets: **pT > 20 GeV, |η| < 2.4** (ttHH AN §3.1
lines 239–240; ttH AN §6.1.2 line 825). The names are deliberately verbose:
the historical short names (`tt+b`, `tt+2b`, `tt+bb`) are easy to misread
because the digit refers to **b-hadrons inside one jet**, not to the number
of b-jets.

| Branch | AN short name | Definition |
|--------|---------------|------------|
| `ttCat_LightFlavour`  | tt+LF        | No additional b- or c-jet. |
| `ttCat_AddCjet`       | tt+cc / tt+C | ≥1 additional c-jet, no additional b-jet. |
| `ttCat_Add1Bjet_1Had` | tt+b         | 1 additional b-jet with 1 b-hadron (wide-angle g→bb, one b out of acceptance). |
| `ttCat_Add1Bjet_2Had` | tt+2b        | 1 additional b-jet with ≥2 b-hadrons (collinear g→bb merged into one jet). |
| `ttCat_Add2Bjet`      | tt+bb        | ≥2 additional b-jets. Also absorbs tt+bbb and tt+4b. |

The physical distinction between `tt+b` and `tt+2b` is the **g→bb opening
angle**: a wide-angle splitting puts the two b's in separate jets (one often
out of acceptance → one reconstructed b-jet with one b-hadron, `tt+b`); a
collinear splitting merges them into a single jet carrying two b-hadrons
(`tt+2b`).

---

## 5. Why five categories and not seven

The ttHH AN §3.2 also defines `tt+bbb` (≥3 additional b-jets) and `tt+4b`
(=4 additional b-jets). The scheme deliberately does **not** split these out,
for three reasons:

1. **GenTtbarCategorizer cannot distinguish them.** Codes 53/54/55 encode the
   b-hadron multiplicity inside the *leading two* additional b-jets only; the
   actual jet count (2, 3, 4, …) is never stored in the integer. Recovering
   bbb-vs-4b from `genTtbarId` is information-theoretically impossible.
2. **The AN constructs bbb/4b at sample level**, not per event (§3.4
   Option1/Option2): via a dedicated LO `tt+4b` sample, or the
   high-multiplicity tail of NLO 4FS `tt+bb`. Neither uses per-event
   GenHFHadronMatcher labelling to separate them.
3. **The final analysis merges them anyway.** ttHH AN §3.4: *"tt+bbb and
   tt+4b are also combined into one class tt+nb, … used as one of the output
   nodes in the DNN."* The bbb-vs-4b split has no effect on the discriminant.

So `ttCat_Add2Bjet` (tt+bb) is a single bucket covering tt+bb, tt+bbb, and
tt+4b — and that **matches the AN's per-event resolution**. A raw-GenPart
algorithm *could* separate bbb from 4b (it counts b-jets directly), so if a
future analysis needs the split the capability exists; only a branch
declaration would need extending. See
[`02_legacy_ttbar_pipeline.md`](02_legacy_ttbar_pipeline.md) §2 for that algorithm.

---

## 6. Samples involved in stitching

For reference, the categories map onto these sample roles (full dataset list
in [`legacy/code/crabConfig/config_ttHH2017UL_categorizer.yaml`](legacy/code/crabConfig/config_ttHH2017UL_categorizer.yaml)):

- **Inclusive 5FS ttbar** (`TTToHadronic`, `TTToSemiLeptonic`, `TTTo2L2Nu`) —
  source of tt+LF and tt+cc after stitching cuts.
- **Dedicated 4FS** (`TTbb_4f_*`) — source of the additional-b categories
  (tt+b / tt+2b / tt+bb), with ME-level extra b-quarks.
- Plus signal (`TTHHTo4b`), QCD HT-binned (crucial for the hadronic channel),
  single top, diboson, V+jets, and rare top/Higgs processes as separate
  backgrounds; and data (`JetHT`, `BTagCSV`, `SingleMuon`).
