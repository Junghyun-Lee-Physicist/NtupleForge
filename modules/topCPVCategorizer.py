"""topCPVCategorizer — NtupleForge NanoAOD-PostProcessor module.

Reproduces the gen-level top-decay categorization of the legacy MiniAOD
``SSBAnalyzer`` (``GenPar()``/``GenJet()``/``GenMET()``/ghost-B) for the
top-CP-violation (CPV) analysis, rebuilding a parton-level family tree from the
NanoAOD ``GenPart`` collection and writing the derived branches.

**Reference of truth = the MiniAOD ``SSBAnalyzer`` code** (see
``docs/TopCPV/03_miniaod_origin.md``), NOT the intermediate standalone
``TopCPVCategorizer``. Where the standalone simplified the MiniAOD logic, this
module follows MiniAOD; the audit in ``docs/TopCPV/02_faithfulness_vs_miniaod.md`` enumerates
every point. The C++ standalone is being brought to the same behaviour, so the
two should agree (validate with ``script/validate_topcpvcat.py``).

Design (see docs/TopCPV/)
-----------------------------
* **Derived branches only.** NtupleForge's default pipeline passes the full
  NanoAOD through, so ``GenPart``, ``GenJet`` (+``hadronFlavour``), ``GenMET``,
  ``GenVisTau`` and ``PSWeight`` already exist in the output ``Events`` tree. This
  module adds **only** the derived quantities, under the ``TopCPVCat_`` prefix,
  and does not re-emit the raw collections (which would collide with the
  passthrough ``GenJet_*`` / ``GenMET_*`` / ``PSWeight_*``). No ``GenCatTree``.
* **MiniAOD-faithful channel.** ``Channel_Idx`` is summed over the **full**
  selected-particle list (MiniAOD §2.1) — so background boson-decay channels are
  recovered, not forced to 0. ``Channel_Idx_Final`` resolves each selected τ to
  its leptonic daughter by **walking the GenPart daughter map** (MiniAOD §2.2),
  and the resolved τ daughter is **appended to the GenPar family tree** exactly as
  MiniAOD's ``FillGenPar`` did (so ``GenPar_Count`` grows for leptonic-τ events).
  ``Channel_Idx == 0`` keeps its MiniAOD meaning: all-hadronic **or**
  unclassifiable.
* **Kept simplifications (audit §3/§4/§6).** Family-tree top is the *last copy*
  (CPV top/antitop momenta come from the faithful ``GenTop``/``GenAnTop``
  branches); W⁻ daughters resolved explicitly; ``GenBJet`` via
  ``GenJet_hadronFlavour`` (which *is* the official ghost-clustering result).
* **NanoAOD additions / unrecoverable (audit §6/§7).** ``Channel_Visible_Tau``
  (from ``nGenVisTau``) and ``Channel_Tau_Lepton`` (# of selected τ → e/μ) are
  NanoAOD-side extras MiniAOD lacks. ``GenBHad`` hadron kinematics use the b-quark
  proxy and ``GenBHad_FromTopWeakDecay`` is recomputed by mother-chain ancestry
  (the official B-hadron collection and B-frag weights are absent from NanoAOD).
* **Diagnostic.** ``Channel_Idx_Expanded`` = ``Channel_Idx``, but ``-999`` when
  ``isSignal`` and the 12-slot build is incomplete (any slot 2–11 < 0 — the
  analogue of MiniAOD's ``SelectedPar.size() != 12``, whose only trace there was a
  ``cerr``). ``Channel_Idx`` itself is untouched. End-of-job line reports the rate.

Input dependency note
---------------------
The categorizer reads ``GenVisTau`` from the input. The MC branch list
(``branches/branch_CPV_Run2_MC.txt``) drops ``GenVisTau*`` from the *output*; fine,
because modules read the full input tree and only the derived
``Channel_Visible_Tau`` is written. Keep ``branch_file`` as an output selection
(NanoAODTools default) so the input ``GenVisTau`` stays readable here.

MC only: if ``GenPart`` is absent (data / non-gen input) the module logs once in
``beginFile`` and becomes a **no-op** (no output branches, ``analyze`` passes
events through). Still: do not add it to data configs — data must run with
``branch_CPV_Run2_Data.txt`` and no gen module.
"""
from __future__ import annotations

import math
import os
import sys

from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

# PyROOT-level NanoAOD access helpers (REQUIRED — see docs/06_nanoaod_branch_access.md):
#  * to_int : UChar_t / Bool_t elements come back as bytes under PyROOT raw
#             proxies, so `x == 5` / `if x:` silently misbehave.
#  * count / opt_count : collection length from the COUNT BRANCH
#             (event.nGenPart, ...). NEVER derive a length by probing the
#             array — TTreeReaderArray.At(i) for i>=size is undefined
#             behaviour in ROOT and segfaults (it does NOT raise a catchable
#             exception). See 06_nanoaod_branch_access.md #2 and
#             05_troubleshooting.md A12. Read elements only in-bounds.
#
# CRAB flattens the sandbox and imports this module FLAT (top-level, no parent
# package), so a relative import cannot work on the worker. Put this file's own
# directory on sys.path so the sibling helper is found regardless of how the
# module was loaded (flat on CRAB, or as `modules.topCPVCategorizer` locally).
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    from nanoaod_branch_access import to_int, count, opt_count   # flat (same dir on sys.path)
except ImportError:                                              # local package context
    from .nanoaod_branch_access import to_int, count, opt_count

# GenPart_statusFlags bit (NanoAODv9). Only the two we use are named here.
_IS_LAST_COPY = 1 << 13
_FROM_HARD_PROCESS = 1 << 8

# GenPar 12-slot static wiring (mother/daughter slot indices), identical to
# TopCPVCategorizer::FillSignalSelection.
_PARENT_SLOT = (-1, -1, -1, -1, 2, 2, 3, 3, 4, 4, 6, 6)
_DAU1_SLOT = (-1, -1, 4, 6, 8, -1, 10, -1, -1, -1, -1, -1)
_DAU2_SLOT = (-1, -1, 5, 7, 9, -1, 11, -1, -1, -1, -1, -1)

_GENPAR_FIELDS = (
    ("Idx", "I"), ("pdgId", "I"), ("Status", "I"),
    ("pt", "F"), ("eta", "F"), ("phi", "F"), ("mass", "F"), ("energy", "F"),
    ("Mom1_Idx", "I"), ("Mom2_Idx", "I"), ("Dau1_Idx", "I"), ("Dau2_Idx", "I"),
    ("Mom_Counter", "I"), ("Dau_Counter", "I"),
)


def _energy(pt: float, eta: float, mass: float) -> float:
    """E from (pt, eta, mass): p = pt*cosh(eta), E = sqrt(p^2 + m^2)."""
    ch = math.cosh(eta)
    return math.sqrt(pt * pt * ch * ch + mass * mass)


class TopCPVCategorizer(Module):
    """NanoAOD reproduction of the MiniAOD SSBAnalyzer gen-level categorization."""

    # Every input branch analyze() reads. Pre-registered in beginFile while the
    # TTreeReader is still clean (eventLoop calls beginFile BEFORE the first
    # gotoEntry), so that NO reader is ever created mid-loop: nanoAOD-tools'
    # treeReaderArrayTools rebuilds ALL readers on a brand-new TTreeReader
    # whenever a reader is added after reading started (_remakeAllReaders),
    # which silently invalidates every reader object bound earlier — the next
    # element access dies with ReferenceError("attempt to access a
    # null-pointer") or a segfault in TObjectArrayReader::At
    # (docs/05_troubleshooting.md A13).
    GEN_ARRAY_BRANCHES = (
        "GenPart_pdgId", "GenPart_statusFlags", "GenPart_genPartIdxMother",
        "GenPart_status", "GenPart_pt", "GenPart_eta", "GenPart_phi",
        "GenPart_mass",
        "GenJet_pt", "GenJet_eta", "GenJet_phi", "GenJet_mass",
        "GenJet_hadronFlavour",
    )
    GEN_COUNTER_BRANCHES = ("nGenPart", "nGenJet", "nGenVisTau")

    _warned_unregistered = False  # one-shot warning flag (see _read_arrays)

    def __init__(self, prefix: str = "TopCPVCat_"):
        self.p = prefix
        self._n_total = 0
        self._n_signal = 0
        self._n_unclassifiable = 0  # isSignal & incomplete 12-slot build
        # Set in beginFile from the input branch list (A5/A11 pattern): True only
        # if GenPart is present. Guards analyze() so a stray data/non-gen file is
        # a no-op instead of a crash. Defaults False so analyze is safe even if
        # beginFile were skipped.
        self._has_genpart = False
        # Guarded validation logging: set env TOPCPVCAT_DEBUG=N to print the
        # derived quantities for the first N events, then stay silent (never
        # logs unboundedly inside the event loop). 0 = off.
        try:
            self._debug_n = int(os.environ.get("TOPCPVCAT_DEBUG", "0") or "0")
        except ValueError:
            self._debug_n = 0

    # -- lifecycle ----------------------------------------------------------
    def beginJob(self):
        pass

    def endJob(self):
        frac = (self._n_unclassifiable / self._n_signal) if self._n_signal else 0.0
        print(
            "[topCPVCategorizer] processed={tot} signal(ttbar)={sig} "
            "unclassifiable(Channel_Idx_Expanded==-999)={bad} ({pct:.3f}% of signal)".format(
                tot=self._n_total, sig=self._n_signal,
                bad=self._n_unclassifiable, pct=100.0 * frac,
            )
        )

    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        # Presence detection via the input branch LIST, not inputTree.GetBranch()
        # nor hasattr(): the nanoAOD-tools InputTree wrapper does not reliably
        # report absence through GetBranch (a data file passed the old
        # `GetBranch("GenPart_pt") is None` guard and crashed in analyze —
        # 05_troubleshooting.md A11), and hasattr() raises RuntimeError on a
        # missing branch rather than returning False (A5). Reading
        # GetListOfBranches() is the robust pattern.
        existing = {b.GetName() for b in inputTree.GetListOfBranches()}
        self._has_genpart = "GenPart_pdgId" in existing
        if not self._has_genpart:
            # MC-only module. Data / non-gen inputs: emit nothing, don't crash.
            print(
                "[topCPVCategorizer] GenPart absent in input (data or non-gen sample) "
                "-> module is a no-op for this file. Keep it out of data configs."
            )
            return

        # Fail fast on a partial gen input rather than crash mid-loop later.
        missing = [b for b in self.GEN_ARRAY_BRANCHES if b not in existing]
        if missing:
            raise RuntimeError(
                "[topCPVCategorizer] input has GenPart but lacks required gen "
                "branches %s — refusing to run on a partial input." % missing
            )

        # Pre-register EVERY reader this module will use, while the TTreeReader
        # is still clean (beginFile runs before the first gotoEntry). After
        # this, no branch access in analyze() ever creates a new reader, so
        # nanoAOD-tools never rebuilds the readers mid-loop and locally bound
        # reader objects stay valid for the whole event loop
        # (docs/05_troubleshooting.md A13, 06_nanoaod_branch_access.md #4).
        array_reader = getattr(inputTree, "arrayReader", None)
        value_reader = getattr(inputTree, "valueReader", None)
        if array_reader is None or value_reader is None:
            print(
                "[topCPVCategorizer] WARNING: InputTree lacks arrayReader/valueReader; "
                "cannot pre-register readers — lazy mid-loop creation may invalidate "
                "bound readers (A13)."
            )
        else:
            n_reg = 0
            for b in self.GEN_ARRAY_BRANCHES:
                array_reader(b)
                n_reg += 1
            for c in self.GEN_COUNTER_BRANCHES:
                if c in existing:
                    value_reader(c)
                    n_reg += 1
            print(
                "[topCPVCategorizer] pre-registered %d gen branch readers "
                "(declare-then-read; keeps the event loop remake-free, A13)" % n_reg
            )

        self.out = wrappedOutputTree
        p = self.p
        b = self.out.branch

        b(p + "isSignal", "O")
        b(p + "SelectedIdx", "I", n=12)

        count = p + "GenPar_Count"
        b(count, "I")
        for name, typ in _GENPAR_FIELDS:
            b(p + "GenPar_" + name, typ, lenVar=count)

        for top in ("GenTop", "GenAnTop"):
            for k in ("pt", "eta", "phi", "energy"):
                b("{0}{1}_{2}".format(p, top, k), "F")

        for c in ("Idx", "Idx_Final", "Lepton_Count", "Lepton_Count_Final",
                  "Jets", "Jets_Abs", "Tau_Lepton", "Visible_Tau"):
            b(p + "Channel_" + c, "I")
        b(p + "Channel_Idx_Expanded", "I")  # additive diagnostic (not in TopCPV)

        bjet_n = p + "GenBJet_Count"
        bhad_n = p + "GenBHad_Count"
        b(bjet_n, "I")
        b(bhad_n, "I")
        for k in ("pt", "eta", "phi", "energy"):
            b(p + "GenBJet_" + k, "F", lenVar=bjet_n)
        for k in ("pt", "eta", "phi", "energy"):
            b(p + "GenBHad_" + k, "F", lenVar=bhad_n)
        b(p + "GenBHad_FromTopWeakDecay", "I", lenVar=bhad_n)
        b(p + "GenBHad_Flavour", "I", lenVar=bhad_n)

    # -- per-event ----------------------------------------------------------
    def analyze(self, event):
        # No-op for files without GenPart (data / non-gen). beginFile already
        # skipped output-branch setup, so writing here would fail anyway.
        if not self._has_genpart:
            return True

        p = self.p
        self._n_total += 1

        # Length from the GenPart COUNT BRANCH (event.nGenPart) — the crash-free
        # canonical NanoAOD length (docs/06_nanoaod_branch_access.md #2, A12).
        # Array readers were pre-registered in beginFile, so these binds create
        # nothing and stay valid; _read_arrays additionally self-heals + warns
        # if a future edit reads an unregistered branch (A13).
        n = count(event, "GenPart")
        (pdg, flg, mom, sta, pt, eta, phi, mass) = self._read_arrays(
            event,
            "GenPart_pdgId", "GenPart_statusFlags", "GenPart_genPartIdxMother",
            "GenPart_status", "GenPart_pt", "GenPart_eta", "GenPart_phi",
            "GenPart_mass",
        )

        # mother-index inversion (NanoAOD has no daughter links)
        daughters = [[] for _ in range(n)]
        for i in range(n):
            m = mom[i]
            if 0 <= m < n:
                daughters[m].append(i)

        sel = [-1] * 12

        # GenPar accumulators
        gp = {k: [] for k in (
            "Idx", "pdgId", "Status", "pt", "eta", "phi", "mass", "energy",
            "Mom1_Idx", "Mom2_Idx", "Dau1_Idx", "Dau2_Idx",
            "Mom_Counter", "Dau_Counter",
        )}

        def push_genpar(idx, mom1, mom2, dau1, dau2):
            if idx < 0:
                gp["Idx"].append(-1)
                gp["pdgId"].append(0)
                gp["Status"].append(0)
                gp["pt"].append(-999.0)
                gp["eta"].append(-999.0)
                gp["phi"].append(-999.0)
                gp["mass"].append(-999.0)
                gp["energy"].append(-999.0)
            else:
                gp["Idx"].append(idx)
                gp["pdgId"].append(int(pdg[idx]))
                gp["Status"].append(int(sta[idx]))
                gp["pt"].append(pt[idx])
                gp["eta"].append(eta[idx])
                gp["phi"].append(phi[idx])
                gp["mass"].append(mass[idx])
                gp["energy"].append(_energy(pt[idx], eta[idx], mass[idx]))
            # mother/daughter counters, identical to TopCPV::PushGenPar
            n_mo, n_da = 2, 2
            if mom1 < 0:
                n_mo -= 1
                if mom2 < 0:
                    n_mo -= 1
                else:
                    mom1 = mom2
            elif mom2 < 0:
                n_mo -= 1
                mom2 = mom1
            elif mom1 == mom2:
                n_mo -= 1
            if dau1 < 0:
                n_da -= 1
                if dau2 < 0:
                    n_da -= 1
                else:
                    dau1 = dau2
            elif dau2 < 0:
                n_da -= 1
                dau2 = dau1
            elif dau1 == dau2:
                n_da -= 1
            gp["Mom1_Idx"].append(mom1)
            gp["Mom2_Idx"].append(mom2)
            gp["Dau1_Idx"].append(dau1)
            gp["Dau2_Idx"].append(dau2)
            gp["Mom_Counter"].append(n_mo)
            gp["Dau_Counter"].append(n_da)

        # -- FindTopAntiTop --------------------------------------------------
        t_idx = tbar_idx = -1
        for i in range(n):
            if not (flg[i] & _IS_LAST_COPY):
                continue
            pid = pdg[i]
            if pid == 6 and t_idx < 0:
                t_idx = i
            if pid == -6 and tbar_idx < 0:
                tbar_idx = i
            if t_idx >= 0 and tbar_idx >= 0:
                break
        sel[2], sel[3] = t_idx, tbar_idx
        is_signal = t_idx >= 0 and tbar_idx >= 0

        def top_kin(idx):
            if idx < 0:
                return (-999.0, -999.0, -999.0, -999.0)
            return (pt[idx], eta[idx], phi[idx], _energy(pt[idx], eta[idx], mass[idx]))

        gen_top = top_kin(t_idx)
        gen_antop = top_kin(tbar_idx)

        # -- selection helpers ----------------------------------------------
        def find_last_daughter(parent, target):
            if parent < 0 or parent >= n:
                return -1
            hit = -1
            for d in daughters[parent]:
                if pdg[d] == target:
                    hit = d
                    break
            if hit < 0:
                return -1
            cur = hit
            while True:
                nxt = -1
                for dd in daughters[cur]:
                    if pdg[dd] == target:
                        nxt = dd
                        break
                if nxt < 0:
                    return cur
                cur = nxt

        def w_daughters(w):
            if w < 0 or w >= n:
                return (-1, -1)
            d1 = d2 = -1
            for d in daughters[w]:
                if abs(pdg[d]) == 24:
                    continue
                if d1 < 0:
                    d1 = d
                elif d2 < 0:
                    d2 = d
                    break
            return (d1, d2)

        if is_signal:
            self._n_signal += 1
            wp = find_last_daughter(t_idx, 24)
            b_q = find_last_daughter(t_idx, 5)
            wm = find_last_daughter(tbar_idx, -24)
            bbar_q = find_last_daughter(tbar_idx, -5)
            sel[4], sel[5], sel[6], sel[7] = wp, b_q, wm, bbar_q
            wp1, wp2 = w_daughters(wp)
            wm1, wm2 = w_daughters(wm)
            sel[8], sel[9], sel[10], sel[11] = wp1, wp2, wm1, wm2
            sel[0] = sel[1] = -1
            for slot in range(12):
                idx = sel[slot]
                mom_i = sel[_PARENT_SLOT[slot]] if _PARENT_SLOT[slot] >= 0 else -1
                dau1 = sel[_DAU1_SLOT[slot]] if _DAU1_SLOT[slot] >= 0 else -1
                dau2 = sel[_DAU2_SLOT[slot]] if _DAU2_SLOT[slot] >= 0 else -1
                push_genpar(idx, mom_i, -1, dau1, dau2)
        else:
            # FillBackgroundSelection: last-copy bosons, their off-flavour
            # daughters, and hard-process last-copy taus.
            picked = []
            for i in range(n):
                if not (flg[i] & _IS_LAST_COPY):
                    continue
                a = abs(pdg[i])
                if a in (6, 23, 24, 25):
                    picked.append(i)
            for k in range(len(picked)):
                bidx = picked[k]
                parent_abs = abs(pdg[bidx])
                for d in daughters[bidx]:
                    if abs(pdg[d]) == parent_abs:
                        continue
                    picked.append(d)
            picked_set = set(picked)
            for i in range(n):
                if not (flg[i] & _FROM_HARD_PROCESS):
                    continue
                if not (flg[i] & _IS_LAST_COPY):
                    continue
                if abs(pdg[i]) != 15:
                    continue
                if i not in picked_set:
                    picked.append(i)
                    picked_set.add(i)
            for idx in picked:
                mom_i = mom[idx]
                dau1 = daughters[idx][0] if len(daughters[idx]) > 0 else -1
                dau2 = daughters[idx][1] if len(daughters[idx]) > 1 else -1
                push_genpar(idx, mom_i, -1, dau1, dau2)

        # -- FinalPar: status 1/2, |pdg| in [11,16] (leptons + neutrinos) ----
        final_par = [i for i in range(n)
                     if (sta[i] == 1 or sta[i] == 2) and 11 <= abs(pdg[i]) <= 16]

        # -- Channel (MiniAOD §2.1 direct) ----------------------------------
        # Iterate the FULL selected-particle list (the pushed GenPar indices),
        # exactly as MiniAOD loops `SelectedPar`. For signal this is identical to
        # slots 8-11 (slots 2-7 carry no leptons); for background it recovers the
        # boson-decay channel TopCPV used to force to 0.
        selected_idx = [i for i in gp["Idx"] if i >= 0]
        selected_set = set(selected_idx)
        channel_idx = channel_lepton = 0
        tau_descendants = {}  # selected-τ index -> its FinalPar descendants (index order)
        for idx in selected_idx:
            a = abs(pdg[idx])
            if a in (11, 13, 15):
                channel_lepton += 1
                channel_idx += (-a if a == 15 else a)   # τ negated
                if a == 15:
                    reach = self._reachable(idx, daughters)
                    tau_descendants[idx] = [f for f in final_par if f in reach]

        # -- Final channel (MiniAOD §2.2: walk each τ to its leptonic daughter)
        # Rewrites the channel and APPENDS the τ daughter to the GenPar family
        # tree (the same FillGenPar the 12 slots used), so GenPar_Count grows for
        # leptonic-τ events — matching MiniAOD. `Channel_Tau_Lepton` is kept as a
        # NanoAOD-side count (# of selected τ that decayed to e/μ).
        channel_lepton_final = channel_lepton
        channel_idx_final = channel_idx
        channel_tau_lepton = 0
        for tau_idx in sorted(tau_descendants):     # std::map iterates in key order
            mom_flag = 0
            mom_pdg = abs(pdg[tau_idx])             # 15
            for dau in tau_descendants[tau_idx]:
                if dau in selected_set:
                    continue
                selected_set.add(dau)
                dau_pdg = abs(pdg[dau])
                if mom_pdg == dau_pdg:
                    continue                        # intermediate τ copy
                if mom_flag == 0:                   # remove the τ once
                    mom_flag = 1
                    channel_lepton_final -= 1
                    if mom_pdg < 14:
                        channel_idx_final -= mom_pdg
                    else:
                        channel_idx_final += mom_pdg
                if dau_pdg in (11, 13, 15):         # charged-lepton daughter
                    push_genpar(dau, tau_idx, -1, -1, -1)
                    channel_lepton_final += 1
                    if dau_pdg < 14:
                        channel_idx_final += dau_pdg
                        channel_tau_lepton += 1     # τ -> e/μ
                    else:
                        channel_idx_final -= dau_pdg

        # Channel_Visible_Tau — NanoAOD bonus (not in MiniAOD). Count branch;
        # 0 if GenVisTau is absent from the input.
        channel_visible_tau = opt_count(event, "GenVisTau")

        # -- ComputeChannelJets ---------------------------------------------
        channel_jets = channel_jets_abs = 0
        if is_signal:
            channel_jets = self._channel_jets(sel, pdg)
            channel_jets_abs = self._channel_jets_abs(channel_jets)

        # -- Channel_Idx_Expanded (additive) --------------------------------
        if is_signal and any(sel[s] < 0 for s in range(2, 12)):
            channel_idx_expanded = -999
            self._n_unclassifiable += 1
        else:
            channel_idx_expanded = channel_idx

        # -- ProcessGenBHadrons ---------------------------------------------
        bjet = {k: [] for k in ("pt", "eta", "phi", "energy")}
        bhad = {k: [] for k in ("pt", "eta", "phi", "energy", "ftwd", "flav")}
        n_gj = count(event, "GenJet")   # count branch; in-bounds indexing below
        (gj_pt, gj_eta, gj_phi, gj_mass, gj_hflav) = self._read_arrays(
            event,
            "GenJet_pt", "GenJet_eta", "GenJet_phi", "GenJet_mass",
            "GenJet_hadronFlavour",
        )
        for i in range(n_gj):
            if to_int(gj_hflav[i]) != 5:   # UChar_t -> coerce (bytes under PyROOT)
                continue
            jpt, jeta, jphi = gj_pt[i], gj_eta[i], gj_phi[i]
            bjet["pt"].append(jpt)
            bjet["eta"].append(jeta)
            bjet["phi"].append(jphi)
            bjet["energy"].append(_energy(jpt, jeta, gj_mass[i]))
            bidx = self._nearest_bquark(jeta, jphi, n, pdg, flg, eta, phi)
            if bidx >= 0:
                bhad["pt"].append(pt[bidx])
                bhad["eta"].append(eta[bidx])
                bhad["phi"].append(phi[bidx])
                bhad["energy"].append(_energy(pt[bidx], eta[bidx], mass[bidx]))
                bhad["flav"].append(int(pdg[bidx]))
                bhad["ftwd"].append(1 if self._ancestor_top(bidx, pdg, mom) else 0)
            else:
                bhad["pt"].append(-999.0)
                bhad["eta"].append(-999.0)
                bhad["phi"].append(-999.0)
                bhad["energy"].append(-999.0)
                bhad["flav"].append(0)
                bhad["ftwd"].append(0)
        n_b = len(bjet["pt"])

        # -- write -----------------------------------------------------------
        fb = self.out.fillBranch
        fb(p + "isSignal", is_signal)
        fb(p + "SelectedIdx", sel)

        fb(p + "GenPar_Count", len(gp["Idx"]))
        for name, _ in _GENPAR_FIELDS:
            fb(p + "GenPar_" + name, gp[name])

        for top, vals in (("GenTop", gen_top), ("GenAnTop", gen_antop)):
            for k, v in zip(("pt", "eta", "phi", "energy"), vals):
                fb("{0}{1}_{2}".format(p, top, k), v)

        fb(p + "Channel_Idx", channel_idx)
        fb(p + "Channel_Idx_Final", channel_idx_final)
        fb(p + "Channel_Lepton_Count", channel_lepton)
        fb(p + "Channel_Lepton_Count_Final", channel_lepton_final)
        fb(p + "Channel_Jets", channel_jets)
        fb(p + "Channel_Jets_Abs", channel_jets_abs)
        fb(p + "Channel_Tau_Lepton", channel_tau_lepton)
        fb(p + "Channel_Visible_Tau", channel_visible_tau)
        fb(p + "Channel_Idx_Expanded", channel_idx_expanded)

        fb(p + "GenBJet_Count", n_b)
        fb(p + "GenBHad_Count", n_b)
        for k in ("pt", "eta", "phi", "energy"):
            fb(p + "GenBJet_" + k, bjet[k])
        for k in ("pt", "eta", "phi", "energy"):
            fb(p + "GenBHad_" + k, bhad[k])
        fb(p + "GenBHad_FromTopWeakDecay", bhad["ftwd"])
        fb(p + "GenBHad_Flavour", bhad["flav"])

        if self._n_total <= self._debug_n:
            print(
                "[topCPVCategorizer:debug] evt#{i} isSignal={sig} "
                "Channel_Idx={ci} Idx_Final={cf} Idx_Expanded={ce} Jets={cj} "
                "Lep={cl}/Final={clf} TauLep={tl} VisTau={vt} "
                "GenPar_Count={gpc} GenBJet_Count={bj}".format(
                    i=self._n_total, sig=int(is_signal),
                    ci=channel_idx, cf=channel_idx_final, ce=channel_idx_expanded,
                    cj=channel_jets, cl=channel_lepton, clf=channel_lepton_final,
                    tl=channel_tau_lepton, vt=channel_visible_tau,
                    gpc=len(gp["Idx"]), bj=n_b,
                )
            )

        return True

    # -- channel-jets digit codes (identical to TopCPV) ---------------------
    @staticmethod
    def _channel_jets(sel, pdg):
        ch_jets = 0
        for k, (s_d1, s_d2) in enumerate(((8, 9), (10, 11))):  # k=0 W+, k=1 W-
            d1, d2 = sel[s_d1], sel[s_d2]
            if d1 < 0 or d2 < 0:
                continue
            p1, p2 = abs(pdg[d1]), abs(pdg[d2])
            if p1 >= 10 or p2 >= 10:  # not a quark pair (leptonic W)
                continue
            if k == 0:  # W+ : up-type (even) first
                code = (10 * p1 + p2) if p1 % 2 == 0 else (p1 + 10 * p2)
            else:       # W- : down-type (odd) first
                code = (10 * p1 + p2) if p1 % 2 == 1 else (p1 + 10 * p2)
            ch_jets = code if ch_jets == 0 else (100 * ch_jets + code)
        return ch_jets

    @staticmethod
    def _channel_jets_abs(ch_jets):
        a = ch_jets
        if a > 0:
            if (a // 10) % 10 > a % 10:
                a = 100 * (a // 100) + 10 * (a % 10) + (a // 10) % 10
            if a // 1000 > (a // 100) % 10:
                a = 1000 * ((a // 100) % 10) + 100 * (a // 1000) + (a % 100)
            if a // 100 > a % 100:
                a = 100 * (a % 100) + a // 100
        return a

    # -- ghost-B helpers (identical to TopCPV) ------------------------------
    @staticmethod
    def _nearest_bquark(jeta, jphi, n, pdg, flg, eta, phi, max_dr=0.4):
        best = -1
        best_dr2 = max_dr * max_dr
        for i in range(n):
            if abs(pdg[i]) != 5:
                continue
            if not (flg[i] & _IS_LAST_COPY):
                continue
            deta = eta[i] - jeta
            dphi = phi[i] - jphi
            while dphi > math.pi:
                dphi -= 2.0 * math.pi
            while dphi < -math.pi:
                dphi += 2.0 * math.pi
            dr2 = deta * deta + dphi * dphi
            if dr2 < best_dr2:
                best_dr2 = dr2
                best = i
        return best

    @staticmethod
    def _ancestor_top(idx, pdg, mom, max_depth=100):
        cur = idx
        depth = 0
        while cur >= 0 and depth < max_depth:
            if abs(pdg[cur]) == 6:
                return True
            cur = mom[cur]
            depth += 1
        return False

    @staticmethod
    def _reachable(start, daughters):
        """GenPart indices reachable from `start` via the daughter map (excl. start)."""
        seen = set()
        stack = list(daughters[start])
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack.extend(daughters[x])
        return seen

    # -- remake-safe multi-branch binding -------------------------------------
    def _read_arrays(self, event, *names):
        """Bind several array readers at once, safely w.r.t. reader remakes.

        With every branch pre-registered in beginFile this is a plain read.
        Safety net: if a future edit reads a branch that was NOT
        pre-registered, its first access makes nanoAOD-tools rebuild ALL
        readers on a new TTreeReader (_remakeAllReaders), silently
        invalidating any reader object obtained earlier in this pass (the next
        element access raises ReferenceError or segfaults — A13). So if the
        reader version changed during the pass, read everything once more (all
        readers exist now, so the second pass is stable) and warn once so the
        registration list gets fixed.
        """
        tree = getattr(event, "_tree", None)
        v0 = getattr(tree, "_ttreereaderversion", None)
        vals = [getattr(event, nm) for nm in names]
        if v0 is not None and tree._ttreereaderversion != v0:
            vals = [getattr(event, nm) for nm in names]  # re-bind on the fresh readers
            if not TopCPVCategorizer._warned_unregistered:
                TopCPVCategorizer._warned_unregistered = True
                print(
                    "[topCPVCategorizer] WARNING: reader rebuild during array "
                    "binding — one of %s is missing from GEN_ARRAY_BRANCHES; add "
                    "it so the hot loop stays remake-free (A13)." % (names,)
                )
        return vals


# NtupleForge entry point (cf. modules/noop.py, modules/jetsMETcut.py)
MODULES = [TopCPVCategorizer()]
