import FWCore.ParameterSet.Config as cms
process = cms.Process('NANO')
process.source = cms.Source("PoolSource", fileNames = cms.untracked.vstring(),)
process.maxEvents = cms.untracked.PSet(input = cms.untracked.int32(10))
# Rule 6: this filename is hardcoded in TWO places — here and in
# crab/submit_crab.py (out_name). They must stay identical.
# 2026-07-26: renamed slimmedNtuple.root -> forgedNtuple.root (D-F).
process.output = cms.OutputModule("PoolOutputModule", fileName = cms.untracked.string('forgedNtuple.root'))
process.out = cms.EndPath(process.output)
