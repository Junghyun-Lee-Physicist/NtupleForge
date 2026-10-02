#!/usr/bin/env python3
# test_jsonpog_inventory.py -- offline test of script/jsonpog_inventory.py on a synthetic payload tree.
#
# Builds a fake jsonpog-integration root (POG/<pog>/<era>/*.json[.gz]) whose files have the node types of
# correctionlib schema v2 (category with string and int keys and a default, binning with list and uniform
# edges, multibinning, formula, transform, compound corrections), a corrupt gzip, a non-json file, an era
# outside the default regex and a missing POG, then checks the inventory lines and exit codes.
# All numbers in the fake files are synthetic (0.111, 0.222, ...): nothing here is a real payload value.
#
#   python3 script/test_jsonpog_inventory.py        # prints PASS/FAIL per check, exit 0 if all pass
import gzip
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "jsonpog_inventory.py")


def corr(name, inputs, out, data, desc="", version=1):
    return {"name": name, "version": version, "description": desc,
            "inputs": [{"name": n, "type": t} for n, t in inputs],
            "output": {"name": out[0], "type": out[1]}, "data": data}


def cat(inp, items, default=None):
    d = {"nodetype": "category", "input": inp, "content": [{"key": k, "value": v} for k, v in items]}
    if default is not None:
        d["default"] = default
    return d


def write(path, cset, gz=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if gz:
        with gzip.open(path, "wt") as f:
            json.dump(cset, f)
    else:
        with open(path, "w") as f:
            json.dump(cset, f)


def cs(corrs, comps=None, desc="synthetic"):
    d = {"schema_version": 2, "description": desc, "corrections": corrs}
    if comps:
        d["compound_corrections"] = comps
    return d


def build(root):
    mb = {"nodetype": "multibinning", "inputs": ["abseta", "pt"], "edges": [[0, 1.2, 2.5], [20, 50, 1000]],
          "content": [1.01, 1.02, 1.03, 1.04], "flow": "clamp"}
    kinfit = cat("systematic", [(s, cat("working_point", [(w, cat("flavor", [(4, mb), (5, mb)]))
                                                          for w in ["L", "M", "T"]])) for s in ["central", "down", "up"]])
    write(os.path.join(root, "POG/BTV/2024_Summer24/btagging.json.gz"), cs([
        corr("UParTAK4_wp_values", [("working_point", "string")], ("wp", "real"),
             cat("working_point", [("L", 0.111), ("M", 0.222), ("T", 0.333), ("XT", 0.444), ("XXT", 0.555)]),
             desc="synthetic | WP thresholds"),
        corr("UParTAK4_kinfit", [("systematic", "string"), ("working_point", "string"), ("flavor", "int"),
                                 ("abseta", "real"), ("pt", "real")], ("weight", "real"), kinfit),
        corr("Synth_flavor_table", [("flavor", "int"), ("pt", "real")], ("weight", "real"),
             cat("flavor", [(5, 1.1), (4, 1.2)], default={"nodetype": "binning", "input": "pt", "edges": [20, 50, 100],
                                                            "content": [0.9, 0.95], "flow": "clamp"})),
        corr("Synth_number_default", [("wp", "string")], ("x", "real"), cat("wp", [("a", 0.1)], default=0.5)),
        corr("Synth_mixed_bins", [("type", "string"), ("pt", "real")], ("x", "real"),
             cat("type", [("a", {"nodetype": "binning", "input": "pt", "edges": [0, 10, 20], "content": [1, 2],
                                 "flow": "clamp"}),
                          ("b", {"nodetype": "binning", "input": "pt", "edges": [0, 5, 10, 15, 20, 30],
                                 "content": [1, 2, 3, 4, 5], "flow": "clamp"})])),
    ]))
    formula = {"nodetype": "formula", "expression": "1+0.0*x", "parser": "TFormula", "variables": ["pt"]}
    shape = cat("systematic", [(s, cat("flavor", [(f, {"nodetype": "binning", "input": "eta",
                                                       "edges": {"n": 4, "low": -2.5, "high": 2.5},
                                                       "content": [formula] * 4, "flow": "error"})
                                                  for f in [0, 4, 5]])) for s in ["central", "up_jes", "down_jes"]])
    write(os.path.join(root, "POG/BTV/2017_UL/btagging.json.gz"), cs([
        corr("deepJet_shape", [("systematic", "string"), ("flavor", "int"), ("eta", "real"), ("pt", "real"),
                               ("discriminant", "real")], ("weight", "real"), shape)]))
    veto = cat("type", [(t, {"nodetype": "multibinning", "inputs": ["eta", "phi"],
                             "edges": [[-5.2, 0, 5.2], [-3.1416, 0, 3.1416]], "content": [0, 100, 0, 0],
                             "flow": "clamp"}) for t in ["jetvetomap", "jetvetomap_all", "jetvetomap_hot"]])
    write(os.path.join(root, "POG/JME/2024_Summer24/jetvetomaps.json.gz"), cs([
        corr("Synthetic24_RunCDEFGHI_V1", [("type", "string"), ("eta", "real"), ("phi", "real")],
             ("vetomap", "real"), veto)]))
    jid = {"nodetype": "binning", "input": "eta", "edges": [-5, -2.7, 2.7, 5],
           "content": [formula, {"nodetype": "transform", "input": "chHEF", "rule": formula, "content": 1.0},
                       formula], "flow": "clamp"}
    write(os.path.join(root, "POG/JME/2024_Summer24/jetid.json"), cs([
        corr("AK4PUPPI_Tight", [("eta", "real"), ("chHEF", "real"), ("multiplicity", "int")], ("id", "int"), jid),
        corr("AK4PUPPI_TightLeptonVeto", [("eta", "real"), ("chHEF", "real")], ("id", "int"), jid)]),
        gz=False)
    jerc = [corr("Synth24_V%d_MC_L2Relative_AK4PFPuppi" % i, [("JetEta", "real"), ("JetPt", "real")],
                 ("correction", "real"), {"nodetype": "binning", "input": "JetEta", "edges": [-5, 5],
                                          "content": [formula], "flow": "clamp"}) for i in range(250)]
    write(os.path.join(root, "POG/JME/2024_Summer24/jet_jerc.json.gz"), cs(jerc, comps=[
        {"name": "Synth24_V1_MC_L1L2L3Res_AK4PFPuppi", "inputs": [{"name": "JetPt", "type": "real"}],
         "output": {"name": "correction", "type": "real"}, "inputs_update": ["JetPt"],
         "input_op": "*", "output_op": "*", "stack": ["Synth24_V1_MC_L2Relative_AK4PFPuppi"]}]))
    with open(os.path.join(root, "POG/JME/2024_Summer24/README.md"), "w") as f:
        f.write("not a payload\n")
    pu = cat("weights", [(w, {"nodetype": "binning", "input": "NumTrueInteractions",
                              "edges": [0, 10, 20, 99], "content": [0.9, 1.0, 1.1], "flow": "clamp"})
                         for w in ["nominal", "up", "down"]], default=1.0)
    write(os.path.join(root, "POG/LUM/2024_Summer24/puWeights.json.gz"), cs([
        corr("Synthetic24_goldenJSON", [("NumTrueInteractions", "real"), ("weights", "string")],
             ("weight", "real"), pu)]))
    write(os.path.join(root, "POG/LUM/2022_Summer22/puWeights.json.gz"), cs([
        corr("Synthetic22", [("weights", "string")], ("weight", "real"), cat("weights", [("nominal", 1.0)]))]))
    os.makedirs(os.path.join(root, "POG/MUO/2024_Summer24"), exist_ok=True)
    with open(os.path.join(root, "POG/MUO/2024_Summer24/muon_Z.json.gz"), "wb") as f:
        f.write(b"\x1f\x8b this is not gzip")


def run(*args):
    p = subprocess.run([sys.executable, TOOL] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    return p.returncode, p.stdout.splitlines(), p.stderr


def main():
    npass = nfail = 0

    def ck(label, cond):
        nonlocal npass, nfail
        if cond:
            npass += 1
            print("PASS " + label)
        else:
            nfail += 1
            print("FAIL " + label)

    with tempfile.TemporaryDirectory() as root:
        build(root)
        rc, lines, err = run("--root", root)
        has = lambda pre: [x for x in lines if x.startswith(pre)]
        ck("default run: exit 3 (corrupt MUO file, EGM missing)", rc == 3)
        ck("ERR for the corrupt gzip names the file", any(x.startswith("ERR|MUO|2024_Summer24|muon_Z.json.gz|")
                                                         for x in lines))
        ck("ERR for the missing EGM directory", any(x.startswith("ERR|EGM|") and "no directory" in x for x in lines))
        ck("POGDIR lists every era, even ones not read",
           "POGDIR|LUM|eras=2022_Summer22,2024_Summer24" in lines)
        ck("era outside the regex is not read", not any("2022_Summer22|puWeights" in x for x in has("FILE|")))
        ck("ERADIR shows the non-json file", any(x.startswith("ERADIR|JME|2024_Summer24|files=3|other=README.md")
                                                for x in lines))
        ck("VALUES gives the WP numbers in key order",
           "VALUES|BTV|2024_Summer24|btagging.json.gz|UParTAK4_wp_values|working_point: "
           "L=0.111, M=0.222, T=0.333, XT=0.444, XXT=0.555" in lines)
        ck("'|' inside a description is replaced", any("|UParTAK4_wp_values|v=1|in=working_point:string|out=wp:real|"
                                                       "desc=synthetic / WP thresholds" in x for x in lines))
        k = "KEYS|BTV|2024_Summer24|btagging.json.gz|UParTAK4_kinfit|"
        ck("nested category keys: systematic, working_point, int flavor",
           k + "systematic=[central,down,up]" in lines and k + "working_point=[L,M,T]" in lines
           and k + "flavor=[4,5]" in lines)
        e = "EDGES|BTV|2024_Summer24|btagging.json.gz|UParTAK4_kinfit|"
        ck("multibinning edges per input", e + "abseta=[0..2.5] nbins=2 binnings=18" in lines
           and e + "pt=[20..1000] nbins=2 binnings=18" in lines)
        ck("uniform binning edges (2017_UL shape)",
           "EDGES|BTV|2017_UL|btagging.json.gz|deepJet_shape|eta=[-2.5..2.5] nbins=4 binnings=9" in lines)
        ck("jet veto map types", "KEYS|JME|2024_Summer24|jetvetomaps.json.gz|Synthetic24_RunCDEFGHI_V1|"
                                 "type=[jetvetomap,jetvetomap_all,jetvetomap_hot]" in lines)
        ck("plain .json read, transform walked (binning under it)",
           "EDGES|JME|2024_Summer24|jetid.json|AK4PUPPI_Tight|eta=[-5..5] nbins=3 binnings=1" in lines)
        ck("big file: names only + SKIP line + compound",
           len([x for x in lines if x.startswith("CORR|JME|2024_Summer24|jet_jerc.json.gz|")]) == 250
           and not any(x.startswith("EDGES|JME|2024_Summer24|jet_jerc") for x in lines)
           and any(x.startswith("SKIP|JME|2024_Summer24|jet_jerc.json.gz|250 corrections") for x in lines)
           and "COMPOUND|JME|2024_Summer24|jet_jerc.json.gz|Synth24_V1_MC_L1L2L3Res_AK4PFPuppi|"
               "stack=Synth24_V1_MC_L2Relative_AK4PFPuppi|in=JetPt" in lines)
        ck("category default walked, string keys", "KEYS|LUM|2024_Summer24|puWeights.json.gz|Synthetic24_goldenJSON|"
                                                   "weights=[nominal,up,down]" in lines)
        ck("SUMMARY counts", lines[-1] == "SUMMARY|files=7|corrections_printed=260|errors=2")
        ck("VALUES flags a default sub-tree", "VALUES|BTV|2024_Summer24|btagging.json.gz|Synth_flavor_table|flavor: 5=1.1, 4=1.2 "
                                              "| default=node" in lines)
        ck("VALUES shows a numeric default", "VALUES|BTV|2024_Summer24|btagging.json.gz|Synth_number_default|wp: a=0.1 "
                                             "| default=0.5" in lines)
        ck("EDGES nbins as min-max over the binnings",
           "EDGES|BTV|2024_Summer24|btagging.json.gz|Synth_mixed_bins|pt=[0..30] nbins=2-5 binnings=2" in lines)

        rc, lines, err = run("--root", root, "--pog", "BTV", "JME", "LUM")
        ck("clean subset: exit 0", rc == 0 and lines[-1].endswith("|errors=0"))
        rc, lines, err = run("--root", root, "--pog", "JME", "--full", "--era-regex", "^2024")
        ck("--full: detail for the big file too", rc == 0 and
           "EDGES|JME|2024_Summer24|jet_jerc.json.gz|Synth24_V7_MC_L2Relative_AK4PFPuppi|JetEta=[-5..5] nbins=1 "
           "binnings=1" in lines and not any(x.startswith("SKIP|") for x in lines))
        rc, lines, err = run("--root", root, "--file", "POG/BTV/2024_Summer24/btagging.json.gz",
                             "--name-regex", "wp_values")
        ck("--file + --name-regex", rc == 0 and [x.split("|")[4] for x in lines if x.startswith("CORR|")]
           == ["UParTAK4_wp_values"] and any(x.startswith("FILE|BTV|2024_Summer24|btagging.json.gz|") for x in lines))
        rc, lines, err = run("--root", root, "--pog", "JME", "--era-regex", "^2024", "--name-regex", "_V1[0-2]_MC_")
        ck("--name-regex narrows a big file below --max-detail: detail, no SKIP", rc == 0 and
           len([x for x in lines if x.startswith("CORR|JME|2024_Summer24|jet_jerc.json.gz|")]) == 3 and
           len([x for x in lines if x.startswith("EDGES|JME|2024_Summer24|jet_jerc.json.gz|")]) == 3 and
           not any(x.startswith("SKIP|") for x in lines))
        rc, lines, err = run("--root", root, "--pog", "JME", "--era-regex", "^2024", "--name-regex", "AK4PFPuppi")
        ck("--name-regex matching more than --max-detail: SKIP says 'matching'",
           any(x.startswith("SKIP|JME|2024_Summer24|jet_jerc.json.gz|250 corrections matching over") for x in lines))
        rc, lines, err = run("--root", root, "--file", "POG/BTV/2024_Summer24/nothere.json.gz")
        ck("--file missing: ERR and exit 3", rc == 3 and any(x.startswith("ERR|BTV|2024_Summer24|nothere.json.gz|")
                                                            for x in lines))
        rc, lines, err = run("--root", os.path.join(root, "nope"))
        ck("missing root: exit 2, message on stderr", rc == 2 and "is not a directory" in err and not lines)
        rc, lines, err = run("--root", root, "--era-regex", "(")
        ck("bad regex: exit 2", rc == 2 and "bad regex" in err)
    print("RESULT: %d PASS, %d FAIL" % (npass, nfail))
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
