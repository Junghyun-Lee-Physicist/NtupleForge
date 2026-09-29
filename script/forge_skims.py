#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forge_skims.py -- the event selections ("skims") that NtupleForge applies in
production, defined in ONE place (docs/12_fastpath_workflow_plan.md section 2.3).

Each skim is written twice, on purpose:

  formula  TTreeFormula string handed to NanoAODTools PostProcessor(cut=...).
           With no python module (modules/noop.py) NanoAODTools selects with
           TTree::Draw('>>elist', cut) and copies with CopyTree: all C++.
  rvec     the same selection written with ROOT::VecOps for RDataFrame.
           script/forge_audit.py evaluates it on every input event,
           independently of the formula; closure C1 requires the number of
           events in the output == the number the rvec expression passes.

Both act on the Jet_pt stored in NanoAOD (central JEC applied, before the
analyzer's own JES/JER), jets with abs(eta) < 2.5. The formula strings are the
ones script/size_options.py measured on 2026-09-28 (its SKIMS; ledger V47);
script/test_forge_audit_mock.py fails if the two tables drift apart.
Decision for 2024: 6j20 (docs/03_DECISIONS.md D-2026-09-28-volume).

No ROOT here: submit_crab.py (preflight) and the tests import it anywhere.
ASCII only, python 3.6 compatible.
"""

JET_ETA_MAX = 2.5

# (name, formula, rvec). forge_ht() is declared by forge_audit.py (C++): the
# scalar pt sum of the jets passing pt > ptmin and abs(eta) < etamax, summed in
# double like TTreeFormula's Sum$ (a float RVec Sum would round differently).
SKIMS = [
    ("6jcount",
     "Sum$(abs(Jet_eta)<2.5)>=6",
     "Sum(abs(Jet_eta)<2.5)>=6"),
    ("6j20",
     "Sum$(Jet_pt>20 && abs(Jet_eta)<2.5)>=6",
     "Sum(Jet_pt>20 && abs(Jet_eta)<2.5)>=6"),
    ("6j25",
     "Sum$(Jet_pt>25 && abs(Jet_eta)<2.5)>=6",
     "Sum(Jet_pt>25 && abs(Jet_eta)<2.5)>=6"),
    ("6j30",
     "Sum$(Jet_pt>30 && abs(Jet_eta)<2.5)>=6",
     "Sum(Jet_pt>30 && abs(Jet_eta)<2.5)>=6"),
    ("6j20ht400",
     "Sum$(Jet_pt>20 && abs(Jet_eta)<2.5)>=6 && Sum$(Jet_pt*(Jet_pt>20 && abs(Jet_eta)<2.5))>400",
     "Sum(Jet_pt>20 && abs(Jet_eta)<2.5)>=6 && forge_ht(Jet_pt, Jet_eta, 20., 2.5)>400"),
]

NONE = "none"
NAMES = [NONE] + [n for n, _, _ in SKIMS]


def get(name):
    """(formula, rvec) of a skim; (None, None) for 'none'. KeyError if unknown."""
    if name in (None, "", NONE):
        return None, None
    for n, formula, rvec in SKIMS:
        if n == name:
            return formula, rvec
    raise KeyError("unknown skim %r (known: %s)" % (name, ", ".join(NAMES)))


if __name__ == "__main__":
    for n, formula, rvec in SKIMS:
        print("%-10s formula: %s\n%-10s rvec   : %s" % (n, formula, "", rvec))
