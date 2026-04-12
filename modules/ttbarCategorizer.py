"""
ttbarCategorizer.py — NtupleForge module for ttbar event categorization.

Purpose
=======
For every event, decide which "tt + heavy flavour" category it belongs to
and write a small set of boolean branches to the output ntuple. The
categorization follows the scheme used by both the ttH AN and the ttHH
AN, which both rely on the official CMS GenHFHadronMatcher tool. We use
its NanoAOD encoding (the ``genTtbarId`` branch) directly rather than
re-implementing the algorithm in Python.

The Five Categories
===================
The naming convention is verbose by design — the historical short names
(``tt+b``, ``tt+2b``, ``tt+bb``) are easy to misread because the digits
refer to **b-hadrons inside one jet**, not to **the number of b-jets**.
The branches in this ntuple use the full form to remove that ambiguity.

+--------------------------+-------------------+----------------------------+
| Branch                   | AN short name     | Definition                 |
+==========================+===================+============================+
| ttCat_LightFlavour       | tt+LF             | No additional b-jet or     |
|                          |                   | c-jet (besides those from  |
|                          |                   | top decay).                |
+--------------------------+-------------------+----------------------------+
| ttCat_AddCjet            | tt+cc / tt+C      | At least one additional    |
|                          |                   | c-jet, no additional       |
|                          |                   | b-jet.                     |
+--------------------------+-------------------+----------------------------+
| ttCat_Add1Bjet_1Had      | tt+b              | Exactly 1 additional       |
|                          |                   | b-jet containing exactly   |
|                          |                   | 1 b-hadron. (Wide-angle    |
|                          |                   | g→bb with one b out of     |
|                          |                   | acceptance.)               |
+--------------------------+-------------------+----------------------------+
| ttCat_Add1Bjet_2Had      | tt+2b             | Exactly 1 additional       |
|                          |                   | b-jet containing ≥2        |
|                          |                   | b-hadrons. (Collinear      |
|                          |                   | g→bb merged into one jet.) |
+--------------------------+-------------------+----------------------------+
| ttCat_Add2Bjet           | tt+bb             | ≥2 additional b-jets.      |
|                          |                   | Includes the historical    |
|                          |                   | ttHH categories tt+bbb     |
|                          |                   | (≥3 b-jets) and tt+4b      |
|                          |                   | (=4 b-jets) — see "Why     |
|                          |                   | five and not seven" below. |
+--------------------------+-------------------+----------------------------+

"Additional" means: not from the top quark decay chain (t → Wb).
Acceptance for additional jets: ``pT > 20 GeV``, ``|eta| < 2.4``
(ttHH AN §3.1 line 239–240; ttH AN §6.1.2 line 825).

Why Five and Not Seven
======================
The ttHH AN §3.2 defines two extra categories ``tt+bbb`` (≥3 additional
b-jets) and ``tt+4b`` (=4 additional b-jets), bringing the total to 7.
We do **not** split them out for three reasons:

1. **The POG tool cannot distinguish them.** GenHFHadronMatcher's
   GenTtbarCategorizer encodes "≥2 additional b-jets" with three codes
   53/54/55, where the digit only describes the b-hadron multiplicity
   inside the leading 2 jets — the actual jet count is **not** stored.
   See ``$CMSSW_BASE/src/TopQuarkAnalysis/TopTools/plugins/
   GenTtbarCategorizer.cc`` lines 282–300. Recovering bbb-vs-4b would
   require re-implementing the tool from raw GenPart info, which the
   AN explicitly says it does not do.

2. **The ttHH AN constructs bbb/4b at sample level, not event level.**
   §3.4 (line 320–328) describes "Option1" (use dedicated LO ``tt+4b``
   sample for both bbb and 4b classes) and "Option2" (use NLO 4FS
   ``tt+bb`` and slice the high-multiplicity tail). Neither option uses
   per-event GenHFHadronMatcher labelling to separate bbb from 4b.

3. **The final analysis merges them anyway.** ttHH AN §3.4 line 328:
   *"The tt+bbb and tt+4b are also combined into one class tt+nb, which
   is later used as one of the output node in the DNN"*. The split has
   no effect on the final discriminant.

The GenPart-based algorithm that was developed in earlier iterations
(and which **could** distinguish bbb from 4b using mother-chain tracing
on raw GenPart info) is preserved in this module as a cross-check only.
It writes nothing to the production branches; its sole output is the
optional debug CSV. If a future analysis decides to split bbb/4b, the
algorithm can be promoted back to a production role with no rewrite.

Production Output Branches
==========================
Two parallel sets of branches are written for every event. The "Xval"
set holds the GenPart cross-check result and is **always** present,
not gated on debug flags — downstream analyzers must be able to
compare the two algorithms event-by-event without re-running anything.

Primary set (genTtbarId, downstream default for stitching/hist split):

* ``ttCat_LightFlavour``     : Bool
* ``ttCat_AddCjet``          : Bool
* ``ttCat_Add1Bjet_1Had``    : Bool
* ``ttCat_Add1Bjet_2Had``    : Bool
* ``ttCat_Add2Bjet``         : Bool
* ``ttCatSource``            : Int  (0=GENTTBARID, 2=NO_TTBAR, 3=NO_GENTTBARID)

Cross-check set (GenPart algorithm, validation only — never used for
stitching or hist splitting):

* ``ttCatXval_LightFlavour``  : Bool
* ``ttCatXval_AddCjet``       : Bool
* ``ttCatXval_Add1Bjet_1Had`` : Bool
* ``ttCatXval_Add1Bjet_2Had`` : Bool
* ``ttCatXval_Add2Bjet``      : Bool
* ``ttCatXvalSource``         : Int  (0=GENPART, 2=NO_TTBAR, 3=NO_GENINFO)

Source-code 1 in both ``ttCatSource`` and ``ttCatXvalSource`` is
reserved (was a fallback path in earlier versions, now removed).

For non-ttbar events, all ten ttCat[Xval]_* branches are False and
both source codes are 2 (NO_TTBAR).

Two Algorithms, Two Roles
=========================
The primary path (``ttCat_*``) uses the NanoAOD-stored ``genTtbarId``
integer, which is the output of the official CMS GenHFHadronMatcher
plugin. This is the AN-cited tool and is the **only** path used by
downstream stitching and histogram splitting.

The cross-check path (``ttCatXval_*``) re-derives the same five
categories from raw GenPart and GenJet information using a Python
implementation of the same logic (last-copy B/C hadron identification,
top-ancestor walking, ΔR matching to gen-jets in acceptance). It uses
a different algorithmic strategy than the POG ghost-clustering
approach, so the two paths are genuinely independent estimators —
disagreements expose either GenPart-walker weak points or
GenHFHadronMatcher edge cases. They typically agree on >97 % of ttbar
events; the residual disagreements concentrate in the 51/52/53
boundary region (1 b-jet vs 2 b-jets, single vs overlapping hadrons).

The cross-check is **never** used for analysis decisions. Its purpose
is to (1) catch silent failures in either implementation, (2) provide
data for an "algorithmic systematic" if a future analysis needs it,
and (3) make the analyzer↔ntuplizer consistency check trivial — the
analyzer can read both branch sets directly and compare event-by-event.

Validation CSV (Optional, Off by Default)
==========================================
For interactive debugging the module can additionally write a per-event
debug CSV summarising both algorithms' decisions side by side. This is
purely a convenience for offline diff/awk analysis — the same
information is already in the ntuple via the two branch sets, so the
CSV adds nothing for production use. Default off so CRAB jobs do not
produce un-staged output files. Activate with the driver flag
``--ttcat-debug-csv``.

Author / History
================
Originally developed for ttHH(4b) fully hadronic, Run2 2017 NanoAODv9 UL.
Major redesign April 2026: switched primary path from GenPart-based
algorithm to direct genTtbarId decoding (option B' in project transcript)
after confirming via GenTtbarCategorizer.cc source code that the AN-cited
tool does not store bbb-vs-4b distinction.
"""
from __future__ import annotations

import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

# Dual-mode import for the NanoAOD compat helper.
#
# Local development: this file lives at modules/ttbarCategorizer.py and
# the helper sits next to it as modules/_nanoaod_compat.py, so the
# relative import works.
#
# CRAB worker: nanoAOD-tools sandboxes flatten the module files into
# the worker's cwd (/srv), with no package context, so the relative
# import fails with "attempted relative import with no known parent
# package". Fall back to a top-level absolute import in that case.
#
# REQUIREMENT: _nanoaod_compat.py must be included in the CRAB sandbox
# alongside ttbarCategorizer.py. If your submit_crab.py / crab_script.py
# packages the modules/ directory wholesale this is automatic; if it
# adds files explicitly, add modules/_nanoaod_compat.py to the list.
try:
    from ._nanoaod_compat import to_int, safe_len      # local: package
except ImportError:
    from _nanoaod_compat import to_int, safe_len       # CRAB: flat cwd


# ============================================================================
# Constants
# ============================================================================

# Acceptance cuts for additional jets, matching GenHFHadronMatcher defaults
# and ttH AN §6.1.2 / ttHH AN §3.1 (line 239-240).
GEN_JET_PT_MIN: float = 20.0    # GeV
GEN_JET_ETA_MAX: float = 2.4
DR_MATCH_MAX: float = 0.4       # ΔR for B-hadron ↔ gen-jet matching


# Production branch names — exactly one is True per ttbar event.
# Order is fixed: it controls the dispatch order in `_classify_primary`
# and the column order in the endJob confusion matrix.
CAT_LIGHTFLAVOUR    = "ttCat_LightFlavour"
CAT_ADDCJET         = "ttCat_AddCjet"
CAT_ADD1BJET_1HAD   = "ttCat_Add1Bjet_1Had"
CAT_ADD1BJET_2HAD   = "ttCat_Add1Bjet_2Had"
CAT_ADD2BJET        = "ttCat_Add2Bjet"

CATEGORIES: tuple[str, ...] = (
    CAT_LIGHTFLAVOUR,
    CAT_ADDCJET,
    CAT_ADD1BJET_1HAD,
    CAT_ADD1BJET_2HAD,
    CAT_ADD2BJET,
)

# Cross-check (GenPart-based) branch names. Always written alongside the
# primary ttCat_* branches so that downstream analyzers can compare the
# two algorithms event-by-event without re-running the categorization.
# The "Xval" namespace marks them clearly as the validation set, not
# the default for stitching / hist splitting.
XCAT_LIGHTFLAVOUR    = "ttCatXval_LightFlavour"
XCAT_ADDCJET         = "ttCatXval_AddCjet"
XCAT_ADD1BJET_1HAD   = "ttCatXval_Add1Bjet_1Had"
XCAT_ADD1BJET_2HAD   = "ttCatXval_Add1Bjet_2Had"
XCAT_ADD2BJET        = "ttCatXval_Add2Bjet"

XCATEGORIES: tuple[str, ...] = (
    XCAT_LIGHTFLAVOUR,
    XCAT_ADDCJET,
    XCAT_ADD1BJET_1HAD,
    XCAT_ADD1BJET_2HAD,
    XCAT_ADD2BJET,
)

# Map: production branch name → matching cross-check branch name.
# Used by the confusion matrix and CSV writer to keep the two namespaces
# in lockstep without duplicating the order.
_PROD_TO_XVAL: dict[str, str] = dict(zip(CATEGORIES, XCATEGORIES))

# Short labels for CSV / report output. Map: branch name → display string.
_DISPLAY: dict[str, str] = {
    CAT_LIGHTFLAVOUR:  "LightFlavour",
    CAT_ADDCJET:       "AddCjet",
    CAT_ADD1BJET_1HAD: "Add1Bjet_1Had",
    CAT_ADD1BJET_2HAD: "Add1Bjet_2Had",
    CAT_ADD2BJET:      "Add2Bjet",
}

# Sentinel labels used in CSV/report when the production path could not
# label an event. Never appear as branch names.
LBL_NOTT    = "NoTtbar"
LBL_NOGEN   = "NoGenTtbarId"
LBL_UNKNOWN = "Unknown"


# ttCatSource provenance codes (primary path).
SRC_GENTTBARID:    int = 0
# code 1 = reserved (was fallback path; intentionally absent)
SRC_NO_TTBAR:      int = 2
SRC_NO_GENTTBARID: int = 3
_SRC_NAMES: dict[int, str] = {
    SRC_GENTTBARID:    "GENTTBARID",
    SRC_NO_TTBAR:      "NO_TTBAR",
    SRC_NO_GENTTBARID: "NO_GENTTBARID",
}

# ttCatXvalSource provenance codes (cross-check path).
XSRC_GENPART:    int = 0  # GenPart algorithm ran successfully
XSRC_NO_TTBAR:   int = 2  # primary path said no ttbar; xval skipped
XSRC_NO_GENINFO: int = 3  # GenPart / GenJet branches missing in input
_XSRC_NAMES: dict[int, str] = {
    XSRC_GENPART:    "GENPART",
    XSRC_NO_TTBAR:   "NO_TTBAR",
    XSRC_NO_GENINFO: "NO_GENINFO",
}


# ============================================================================
# genTtbarId decoder
#
# This is the primary categorization function. It implements the
# GenTtbarCategorizer.cc encoding (CMSSW TopQuarkAnalysis/TopTools) for
# the last-2-digits part of the 5-digit event ID. The leading 3 digits
# (number of b-jets from top, b-jets from W, c-jets from W) are
# information-only for our purposes — the category is fully determined by
# the modulo-100 part.
#
# Reference: GenTtbarCategorizer.cc lines 268-310.
# Codes:
#   0          → tt+LF
#   41-45      → tt+cc (variants by hadron multiplicity)
#   51         → tt+b   (1 add b-jet, 1 b-hadron)
#   52         → tt+2b  (1 add b-jet, ≥2 b-hadrons; collinear g→bb)
#   53, 54, 55 → tt+bb  (≥2 add b-jets, variants by hadron multiplicity)
# ============================================================================

def decode_genttbarid(genttbarid: int) -> Optional[str]:
    """Map a raw genTtbarId integer to one of the five production categories.

    Returns the category branch name (e.g. ``"ttCat_Add2Bjet"``) on
    success, or ``None`` if the code is unrecognized. ``None`` is
    treated as a sample-level error and triggers a warning at endJob.
    """
    if genttbarid is None or genttbarid < 0:
        return None
    code = genttbarid % 100
    if code == 0:
        return CAT_LIGHTFLAVOUR
    if 41 <= code <= 45:
        return CAT_ADDCJET
    if code == 51:
        return CAT_ADD1BJET_1HAD
    if code == 52:
        return CAT_ADD1BJET_2HAD
    if 53 <= code <= 55:
        return CAT_ADD2BJET
    return None


# ============================================================================
# GenPart-based cross-check algorithm
#
# This is the legacy categorizer, preserved for validation. It is *not*
# used to set production branches. Its results go only to the debug CSV
# and the endJob confusion matrix.
#
# The algorithm:
#   1. Find every "additional" B-hadron in GenPart: status-flag isLastCopy
#      AND no top-quark ancestor in the mother chain.
#   2. Find every gen-jet with hadronFlavour == 5 in (pT, eta) acceptance.
#   3. ΔR-match B-hadrons to b-jets (closest within ΔR < 0.4).
#   4. Count: number of distinct matched b-jets, number of B-hadrons in each.
#   5. Apply the same logic for c-hadrons (skipping events that already
#      have additional b-jets, to follow the AN's "tt+C only if no add b").
#   6. Decide category from the (n_bjet, hadron-multiplicity) combination.
# ============================================================================

def _is_b_hadron(pdgId: int) -> bool:
    """PDG-ID test for any B hadron (meson or baryon, ground or excited)."""
    aid = abs(pdgId)
    if aid < 100:
        return False
    if aid < 1000:
        return (aid // 100) == 5
    if aid < 10000:
        return (aid // 1000) == 5
    base = aid % 10000
    if 100 <= base < 1000:
        return (base // 100) == 5
    if 1000 <= base < 10000:
        return (base // 1000) == 5
    return False


def _is_c_hadron(pdgId: int) -> bool:
    """PDG-ID test for any C hadron, excluding any hadron that is also a B."""
    if _is_b_hadron(pdgId):
        return False
    aid = abs(pdgId)
    if aid < 100:
        return False
    if aid < 1000:
        return (aid // 100) == 4
    if aid < 10000:
        return (aid // 1000) == 4
    base = aid % 10000
    if 100 <= base < 1000:
        return (base // 100) == 4
    if 1000 <= base < 10000:
        return (base // 1000) == 4
    return False


def _delta_r2(eta1: float, phi1: float, eta2: float, phi2: float) -> float:
    deta = eta1 - eta2
    dphi = phi1 - phi2
    pi = 3.141592653589793
    while dphi > pi:
        dphi -= 2 * pi
    while dphi < -pi:
        dphi += 2 * pi
    return deta * deta + dphi * dphi


def _has_top_ancestor(event, idx: int, nGP: int, max_depth: int = 30) -> bool:
    """Walk the mother chain looking for a top quark within max_depth steps.

    Note: this is a known weak point. The POG GenHFHadronMatcher uses
    ghost-clustering and a more sophisticated parton-history walker.
    Marginal disagreements (~2-3% in our TTHHTo4b runs) are expected and
    are the reason we use genTtbarId as primary, not this algorithm.
    """
    cur = idx
    for _ in range(max_depth):
        mother = event.GenPart_genPartIdxMother[cur]
        if mother < 0 or mother >= nGP:
            return False
        if abs(event.GenPart_pdgId[mother]) == 6:
            return True
        cur = mother
    return False


def _categorize_genpart_xval(event, has_genpart: bool, has_genjet: bool) -> Optional[str]:
    """Run the GenPart cross-check algorithm.

    Returns one of the five production category names, or None if the
    required GenPart/GenJet branches are not available in the input.
    """
    if not (has_genpart and has_genjet):
        return None

    nGP = safe_len(event.GenPart_pdgId, branch_name="GenPart_pdgId")
    nGJ = safe_len(event.GenJet_pt,    branch_name="GenJet_pt")

    # ----- additional B hadrons -----
    add_bh: list[tuple[float, float]] = []
    for i in range(nGP):
        if not _is_b_hadron(event.GenPart_pdgId[i]):
            continue
        if not ((event.GenPart_statusFlags[i] >> 13) & 1):  # isLastCopy
            continue
        if _has_top_ancestor(event, i, nGP):
            continue
        add_bh.append((event.GenPart_eta[i], event.GenPart_phi[i]))

    # ----- gen b-jets in acceptance -----
    bjet_indices: list[int] = []
    for j in range(nGJ):
        # GenJet_hadronFlavour is UChar_t — see _nanoaod_compat for why
        # the to_int wrapper is mandatory.
        if to_int(event.GenJet_hadronFlavour[j]) != 5:
            continue
        if event.GenJet_pt[j] < GEN_JET_PT_MIN:
            continue
        if abs(event.GenJet_eta[j]) > GEN_JET_ETA_MAX:
            continue
        bjet_indices.append(j)

    # ----- match B-hadrons to b-jets -----
    jet_bh_map: dict[int, int] = defaultdict(int)
    if add_bh and bjet_indices:
        dr2_cut = DR_MATCH_MAX * DR_MATCH_MAX
        for bh_eta, bh_phi in add_bh:
            best_dr2 = dr2_cut
            best_j = -1
            for j in bjet_indices:
                dr2 = _delta_r2(
                    bh_eta, bh_phi,
                    event.GenJet_eta[j], event.GenJet_phi[j],
                )
                if dr2 < best_dr2:
                    best_dr2 = dr2
                    best_j = j
            if best_j >= 0:
                jet_bh_map[best_j] += 1

    n_add_bjet = len(jet_bh_map)

    # ----- decide category from b-jet count and hadron multiplicity -----
    if n_add_bjet == 1:
        n_had = next(iter(jet_bh_map.values()))
        if n_had == 1:
            return CAT_ADD1BJET_1HAD
        else:
            return CAT_ADD1BJET_2HAD
    if n_add_bjet >= 2:
        return CAT_ADD2BJET

    # No additional b-jet → check for additional c-jets
    add_ch: list[tuple[float, float]] = []
    for i in range(nGP):
        if not _is_c_hadron(event.GenPart_pdgId[i]):
            continue
        if not ((event.GenPart_statusFlags[i] >> 13) & 1):
            continue
        if _has_top_ancestor(event, i, nGP):
            continue
        add_ch.append((event.GenPart_eta[i], event.GenPart_phi[i]))

    if add_ch:
        cjet_indices: list[int] = []
        for j in range(nGJ):
            if to_int(event.GenJet_hadronFlavour[j]) != 4:
                continue
            if event.GenJet_pt[j] < GEN_JET_PT_MIN:
                continue
            if abs(event.GenJet_eta[j]) > GEN_JET_ETA_MAX:
                continue
            cjet_indices.append(j)

        if cjet_indices:
            dr2_cut = DR_MATCH_MAX * DR_MATCH_MAX
            matched: set[int] = set()
            for ch_eta, ch_phi in add_ch:
                best_dr2 = dr2_cut
                best_j = -1
                for j in cjet_indices:
                    dr2 = _delta_r2(
                        ch_eta, ch_phi,
                        event.GenJet_eta[j], event.GenJet_phi[j],
                    )
                    if dr2 < best_dr2:
                        best_dr2 = dr2
                        best_j = j
                if best_j >= 0:
                    matched.add(best_j)
            if matched:
                return CAT_ADDCJET

    return CAT_LIGHTFLAVOUR


# ============================================================================
# Module
# ============================================================================

class TtbarCategorizer(Module):
    """NanoAOD-tools Module that writes the five ttCat_* branches.

    Both the primary (genTtbarId) and cross-check (GenPart) algorithms
    run on every ttbar event in every mode. Their results are written
    to two parallel branch namespaces (``ttCat_*`` and ``ttCatXval_*``)
    so downstream code can compare them. The optional ``debug_csv``
    flag adds a per-event CSV dump for offline awk/diff convenience.

    Constructor parameters
    ----------------------
    debug_csv : bool, default False
        If True, also write a per-event CSV alongside the production
        ntuple. The CSV duplicates information that is already in the
        ntuple branches; it exists purely as a convenience for
        interactive debugging. Default off so CRAB jobs do not produce
        un-staged-out output files.
    debug_csv_path : str or Path, optional
        Where to write the CSV (only effective if debug_csv=True).
        Default: ``./ttcat_debug.csv``.
    quiet : bool, default False
        If True, suppress the endJob stderr report. Default False — the
        report is short and helpful for spotting silent failures in
        CRAB logs.
    """

    # Required input branches. beginFile() will explicitly enable these
    # via SetBranchStatus(name, 1) as a defense against driver-level
    # branchsel filters that might have disabled them.
    _REQUIRED_INPUTS_PRIMARY: tuple[str, ...] = (
        "genTtbarId",
        "run", "luminosityBlock", "event",
    )
    _REQUIRED_INPUTS_XVAL: tuple[str, ...] = (
        "nGenPart", "GenPart_pdgId", "GenPart_eta", "GenPart_phi",
        "GenPart_statusFlags", "GenPart_genPartIdxMother",
        "nGenJet", "GenJet_pt", "GenJet_eta", "GenJet_phi",
        "GenJet_hadronFlavour",
    )

    def __init__(
        self,
        *,
        debug_csv: bool = False,
        debug_csv_path: Optional[Any] = None,
        quiet: bool = False,
    ) -> None:
        super().__init__()
        self._debug_csv_enabled = debug_csv
        self._debug_csv_path = (
            Path(debug_csv_path) if debug_csv_path is not None
            else Path("ttcat_debug.csv")
        )
        self._quiet = quiet

        # Branch presence flags. Set in beginFile() before any event is
        # processed. False is the safe default — analyze() short-circuits
        # cleanly when a needed branch is absent.
        self._has_genttbarid: bool = False
        self._has_genpart:    bool = False
        self._has_genjet:     bool = False

        # CSV file handle (None until first ttbar event with debug enabled)
        self._csv_fh = None

        # endJob counters
        self._n_total = 0
        self._src_counts: dict[int, int] = defaultdict(int)
        self._cat_counts: dict[str, int] = defaultdict(int)
        # Confusion matrix indexed [production_label][xval_label]
        self._confusion: dict[str, dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._n_xval_attempted = 0
        self._n_xval_agreed = 0

        self._t_start = 0.0

    # ──────────────────────────────────────────────────────────────────
    # framework hooks
    # ──────────────────────────────────────────────────────────────────

    def beginJob(self) -> None:
        self._t_start = time.time()
        sys.stderr.write(
            "[TtbarCategorizer] starting "
            f"(debug_csv={self._debug_csv_enabled}, quiet={self._quiet})\n"
            "  primary path : genTtbarId  -> ttCat_*\n"
            "  cross-check  : GenPart algo -> ttCatXval_*\n"
        )

    def endJob(self) -> None:
        if self._csv_fh is not None:
            self._csv_fh.close()
            self._csv_fh = None
        if not self._quiet:
            self._print_report()

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree) -> None:
        # Defense in depth: explicitly re-enable any required input
        # branches that an upstream branchsel might have disabled.
        # Both the primary (genTtbarId) and cross-check (GenPart)
        # algorithms always run, so all their inputs are always needed.
        existing = {b.GetName() for b in inputTree.GetListOfBranches()}
        wanted = list(self._REQUIRED_INPUTS_PRIMARY) + list(self._REQUIRED_INPUTS_XVAL)
        n_enabled = 0
        n_missing = 0
        for name in wanted:
            if name in existing:
                inputTree.SetBranchStatus(name, 1)
                n_enabled += 1
            else:
                n_missing += 1
        sys.stderr.write(
            f"[TtbarCategorizer] beginFile: re-enabled {n_enabled}/{len(wanted)} "
            f"required input branches ({n_missing} not present in this file)\n"
        )

        # Detect which gen-level inputs are present in this file. Done
        # here (not lazily on the first event) because reading from the
        # input tree's branch list is reliable in all cases, whereas
        # ``hasattr(event, name)`` raises ``RuntimeError`` (not
        # ``AttributeError``) inside nanoAOD-tools' Event wrapper when
        # the branch is missing — and Python 3's ``hasattr`` does NOT
        # catch ``RuntimeError``, so the exception propagates and
        # crashes the job. This is exactly how the categorizer broke
        # on data NanoAOD (no gen branches at all). Reading the branch
        # list directly avoids the wrapper entirely.
        self._has_genttbarid = "genTtbarId"     in existing
        self._has_genpart    = "GenPart_pdgId"  in existing
        self._has_genjet     = "GenJet_pt"      in existing
        sys.stderr.write(
            f"[TtbarCategorizer] beginFile: branch presence: "
            f"genTtbarId={self._has_genttbarid}, "
            f"GenPart_pdgId={self._has_genpart}, "
            f"GenJet_pt={self._has_genjet}\n"
        )

        # Capture the wrapped output tree so analyze() can fill branches.
        # NanoAOD-tools' Module base class does NOT inject self.out
        # automatically — each module must store the reference itself.
        self.out = wrappedOutputTree

        # Declare output branches — primary set, then cross-check set.
        for cat in CATEGORIES:
            wrappedOutputTree.branch(cat, "O")             # Bool
        wrappedOutputTree.branch("ttCatSource", "I")        # Int
        for xcat in XCATEGORIES:
            wrappedOutputTree.branch(xcat, "O")            # Bool
        wrappedOutputTree.branch("ttCatXvalSource", "I")    # Int

    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree) -> None:
        pass

    # ──────────────────────────────────────────────────────────────────
    # main per-event entry point
    # ──────────────────────────────────────────────────────────────────

    def analyze(self, event) -> bool:
        # Reset all category branches to False; the chosen one is set to True.
        for cat in CATEGORIES:
            self.out.fillBranch(cat, False)
        for xcat in XCATEGORIES:
            self.out.fillBranch(xcat, False)

        # ----- Primary path: genTtbarId -----
        production_label, source = self._classify_primary(event)
        if production_label in CATEGORIES:
            self.out.fillBranch(production_label, True)
        self.out.fillBranch("ttCatSource", source)

        # ----- Cross-check path: GenPart algorithm -----
        # Always runs (results are written to ttCatXval_* branches in the
        # ntuple, so downstream comparisons need no re-running). Only the
        # source code differs by the availability of inputs.
        xval_label, xval_source = self._classify_xval(event, source)
        if xval_label in XCATEGORIES:
            self.out.fillBranch(xval_label, True)
        self.out.fillBranch("ttCatXvalSource", xval_source)

        # ----- Bookkeeping -----
        self._n_total += 1
        self._src_counts[source] += 1
        self._cat_counts[production_label] += 1

        # Confusion matrix only meaningful when both algorithms produced
        # a real category (not NO_TTBAR / NO_GENTTBARID / NO_GENINFO).
        if (source == SRC_GENTTBARID
                and xval_source == XSRC_GENPART
                and production_label in CATEGORIES
                and xval_label in XCATEGORIES):
            self._n_xval_attempted += 1
            # Compare in primary-namespace: map xval branch back to its
            # primary equivalent for the matrix.
            xval_as_prod = CATEGORIES[XCATEGORIES.index(xval_label)]
            if xval_as_prod == production_label:
                self._n_xval_agreed += 1
            self._confusion[production_label][xval_as_prod] += 1

        # ----- Optional CSV dump -----
        if self._debug_csv_enabled:
            self._write_csv_row(
                event,
                source, production_label,
                xval_source, xval_label,
            )

        return True

    # ──────────────────────────────────────────────────────────────────
    # internals
    # ──────────────────────────────────────────────────────────────────

    def _classify_primary(self, event) -> tuple[str, int]:
        """Run the primary genTtbarId-based categorization.

        Returns ``(label, source_code)`` where label is either a category
        branch name or one of the ``LBL_*`` sentinels.
        """
        if not self._has_genttbarid:
            return (LBL_NOGEN, SRC_NO_GENTTBARID)
        gtid = int(event.genTtbarId)
        if gtid < 0:
            return (LBL_NOTT, SRC_NO_TTBAR)
        cat = decode_genttbarid(gtid)
        if cat is None:
            return (LBL_UNKNOWN, SRC_GENTTBARID)
        return (cat, SRC_GENTTBARID)

    def _classify_xval(self, event, primary_source: int) -> tuple[str, int]:
        """Run the GenPart-based cross-check categorization.

        Returns ``(xval_branch_name, xval_source_code)``. If the primary
        path already determined the event is not ttbar, the cross-check
        is skipped (no GenPart info would help) and source = NO_TTBAR.
        If GenPart/GenJet branches are missing in the input, source =
        NO_GENINFO.
        """
        # Skip xval entirely on non-ttbar events — there's nothing to
        # cross-check, and forcing the algorithm to walk GenPart of a
        # non-ttbar event would just waste CPU.
        if primary_source == SRC_NO_TTBAR:
            return (LBL_NOTT, XSRC_NO_TTBAR)

        if not (self._has_genpart and self._has_genjet):
            return (LBL_UNKNOWN, XSRC_NO_GENINFO)

        prod_label = _categorize_genpart_xval(
            event, self._has_genpart, self._has_genjet,
        )
        if prod_label is None:
            return (LBL_UNKNOWN, XSRC_NO_GENINFO)

        # Translate primary-namespace label to its xval-namespace twin.
        xval_label = _PROD_TO_XVAL[prod_label]
        return (xval_label, XSRC_GENPART)

    # ----- CSV -----

    def _ensure_csv(self) -> None:
        if self._csv_fh is not None:
            return
        self._debug_csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._csv_fh = self._debug_csv_path.open("w", buffering=1)
        self._csv_fh.write(
            "run,lumi,event,"
            "ttCatSource,ttCatXvalSource,"
            "genTtbarId,genTtbarId_mod100,"
            "cat_production,cat_xval,agree\n"
        )
        sys.stderr.write(
            f"[TtbarCategorizer] writing debug CSV to {self._debug_csv_path}\n"
        )

    def _write_csv_row(
        self,
        event,
        prim_source: int,
        prim_label: str,
        xval_source: int,
        xval_label: str,
    ) -> None:
        self._ensure_csv()
        gtid = int(event.genTtbarId) if self._has_genttbarid else -1
        gtid_mod = (gtid % 100) if gtid >= 0 else -1
        prim_disp = _DISPLAY.get(prim_label, prim_label)
        # xval label might be in xval-namespace; map back to display
        if xval_label in XCATEGORIES:
            xval_disp = _DISPLAY[CATEGORIES[XCATEGORIES.index(xval_label)]]
        else:
            xval_disp = xval_label
        # Agreement only meaningful when both produced a real category
        if prim_source == SRC_GENTTBARID and xval_source == XSRC_GENPART:
            xval_as_prod = (
                CATEGORIES[XCATEGORIES.index(xval_label)]
                if xval_label in XCATEGORIES else xval_label
            )
            agree = "Y" if xval_as_prod == prim_label else "N"
        else:
            agree = "n/a"
        self._csv_fh.write(
            f"{event.run},{event.luminosityBlock},{event.event},"
            f"{_SRC_NAMES.get(prim_source, prim_source)},"
            f"{_XSRC_NAMES.get(xval_source, xval_source)},"
            f"{gtid},{gtid_mod},"
            f"{prim_disp},{xval_disp},{agree}\n"
        )

    # ----- endJob report -----

    def _print_report(self) -> None:
        elapsed = time.time() - self._t_start
        rate = self._n_total / elapsed if elapsed > 0 else 0.0
        out = sys.stderr.write

        out("\n" + "=" * 72 + "\n")
        out("TtbarCategorizer endJob report\n")
        out("=" * 72 + "\n")
        out(f"  total events processed : {self._n_total}\n")
        out(f"  elapsed                : {elapsed:.1f} s ({rate:.1f} Hz)\n")
        out("\n  source distribution:\n")
        for src in (SRC_GENTTBARID, SRC_NO_TTBAR, SRC_NO_GENTTBARID):
            n = self._src_counts.get(src, 0)
            pct = 100.0 * n / self._n_total if self._n_total else 0.0
            out(f"    {_SRC_NAMES[src]:14s} : {n:8d}  ({pct:5.1f} %)\n")

        # Warning if NOGENTTBARID is non-trivial
        n_nogen = self._src_counts.get(SRC_NO_GENTTBARID, 0)
        if n_nogen > 0 and (n_nogen / max(self._n_total, 1)) > 0.05:
            out("\n  ┌" + "─" * 60 + "┐\n")
            out("  │  WARNING: > 5 % of events lack genTtbarId branch.       │\n")
            out("  │  This is unexpected for standard NanoAODv9 ttbar       │\n")
            out("  │  samples. Check the input file production config.      │\n")
            out("  └" + "─" * 60 + "┘\n")

        out("\n  production category counts (genTtbarId):\n")
        for cat in CATEGORIES:
            n = self._cat_counts.get(cat, 0)
            disp = _DISPLAY[cat]
            out(f"    {disp:18s} : {n:8d}\n")
        for sentinel in (LBL_NOTT, LBL_NOGEN, LBL_UNKNOWN):
            n = self._cat_counts.get(sentinel, 0)
            if n > 0:
                out(f"    {sentinel:18s} : {n:8d}\n")

        # Cross-check section — always printed since the algorithm
        # always runs in the new dual-branch architecture.
        if self._n_xval_attempted > 0:
            agree_pct = 100.0 * self._n_xval_agreed / self._n_xval_attempted
            out(f"\n  cross-check (GenPart vs genTtbarId):\n")
            out(f"    attempted : {self._n_xval_attempted}\n")
            out(f"    agreed    : {self._n_xval_agreed}  ({agree_pct:.1f} %)\n")
            self._print_confusion_matrix(out)

        out("=" * 72 + "\n\n")

    def _print_confusion_matrix(self, out) -> None:
        """Render a confusion matrix on stderr.

        Rows = production decision (genTtbarId), columns = xval (GenPart).
        Cells are integer event counts. Trailing column shows row sums.
        """
        col_labels = list(CATEGORIES) + [LBL_UNKNOWN]
        col_disp = [_DISPLAY.get(c, c) for c in col_labels]
        col_w = max(8, max(len(d) for d in col_disp) + 1)

        out("\n    confusion matrix (rows = genTtbarId, cols = GenPart xval):\n")
        header = " " * 22 + "".join(f"{d:>{col_w}}" for d in col_disp) + "    sum\n"
        out(header)
        out(" " * 22 + "─" * (col_w * len(col_disp) + 8) + "\n")

        col_sums = [0] * len(col_labels)
        for row in CATEGORIES:
            row_disp = _DISPLAY[row]
            row_data = self._confusion.get(row, {})
            row_sum = 0
            line = f"      {row_disp:>16s}  "
            for j, col in enumerate(col_labels):
                v = row_data.get(col, 0)
                col_sums[j] += v
                row_sum += v
                line += f"{v:>{col_w}d}"
            line += f"  {row_sum:>6d}\n"
            out(line)

        out(" " * 22 + "─" * (col_w * len(col_disp) + 8) + "\n")
        sum_line = " " * 18 + "sum  "
        for j in range(len(col_labels)):
            sum_line += f"{col_sums[j]:>{col_w}d}"
        sum_line += f"  {sum(col_sums):>6d}\n"
        out(sum_line)


# ============================================================================
# Module factory
#
# This is the canonical way to instantiate the categorizer from a user's
# module-list file when running through `run_postproc.py`. The factory
# reads three environment variables that the driver sets from its
# argparse arguments:
#
#     TTCAT_DEBUG_CSV       — set to "1" to enable per-event CSV dump
#     TTCAT_DEBUG_CSV_PATH  — output path for the CSV (optional)
#     TTCAT_QUIET           — set to "1" to suppress endJob report
#
# Typical usage in a module-list file:
#
#     from modules.ttbarCategorizer import make_default_module
#     MODULES = [make_default_module()]
#
# This indirection lets the driver toggle CSV / quiet behaviour from the
# command line without anyone having to import argparse into the user's
# module-list file.
# ============================================================================

def make_default_module() -> "TtbarCategorizer":
    """Create a TtbarCategorizer with options taken from environment variables.

    See the module factory section above for the variable names.
    Anything not set in the environment falls back to the constructor
    defaults (production mode, no CSV, report on).
    """
    import os
    return TtbarCategorizer(
        debug_csv      = os.environ.get("TTCAT_DEBUG_CSV") == "1",
        debug_csv_path = os.environ.get("TTCAT_DEBUG_CSV_PATH") or None,
        quiet          = os.environ.get("TTCAT_QUIET") == "1",
    )


# ============================================================================
# Module list for run_postproc.py
#
# The driver loads modules via the `package.module:LIST_NAME` syntax
# (e.g. `-I modules.ttbarCategorizer:MODULES`). The list is built once
# at import time by calling the factory, so any TTCAT_* environment
# variables that the driver set BEFORE importing this module are
# automatically picked up.
# ============================================================================

MODULES = [make_default_module()]
