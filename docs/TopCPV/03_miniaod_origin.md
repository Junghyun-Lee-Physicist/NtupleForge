# MiniAOD `SSBAnalyzer` — generator block (progenitor of the categorizer)

> **What this file is.** The NtupleForge `topCPVCategorizer` module reproduces, in
> **NanoAOD**, the generator-level sections of the original **MiniAOD**
> `SSBAnalyzer` EDAnalyzer (the CP-violation ntuplizer authored by S. Ha,
> S. Lee, S. Choi). This document preserves the **original MiniAOD logic and the
> verbatim code** of those sections, so the NanoAOD port can be audited against
> its source of truth. Only the generator-relevant methods are reproduced here —
> `GenPar()`, `GenJet()`, `GenMET()`, the ghost-B section of `analyze()`, and the
> `IndexLinker()` / `FillGenPar()` helpers. The reco objects (muon, electron,
> photon, jet, MET, trigger, vertex, ...) are intentionally omitted.
>
> The faithfulness audit (what the NanoAOD port keeps, changes, or drops relative
> to this code) lives in [`02_faithfulness_vs_miniaod.md`](02_faithfulness_vs_miniaod.md).

---

## 0. The five generator sections of `SSBAnalyzer`

| # | Section | CMSSW input (token) | Output branches |
|---|---|---|---|
| 1 | `GenPar()` | `GenEventInfoProduct`, `GenParticleCollection` | `GenPar_*`, `GenTop`, `GenAnTop`, `Channel_*` |
| 2 | `GenJet()` | `GenJetCollection` | `GenJet`, `GenJet_HCalEnergy`, `GenJet_ECalEnergy` |
| 3 | `GenMET()` | `GenMETCollection` | `GenMET`, `GenMET_Count` |
| 4 | Ghost B-hadron | `genBHadIndex`, `genBHadJetIndex`, `genBHadFromTopWeakDecay`, `genBHadFlavour`, reclustered `GenJetCollection` | `GenBJet`, `GenBHad`, `GenBHad_FromTopWeakDecay`, `GenBHad_Flavour` |
| 5 | B-fragmentation (`doFragSys`) | `bfragWgtProducer:{up,central,down,Peterson}Frag`, `semilepbr{Up,Down}` | `Frag_*_Weight`, `Semilep_Br*_Weight` |

`GenPar()` has **two parallel branches** chosen by hadronizer module name:
`isPYTHIA` (`moduleName` contains `"Pythia"`) and `isHerwig` (contains
`"PEGHadronizer"`). The two are algorithmically parallel; the PYTHIA branch is
the one reproduced below (it is the mother of the NanoAOD port). The HERWIG
branch differs only in status conventions (status `11` for hard process, beam
protons kept) — see §7.

---

## 1. `GenPar()` — PYTHIA branch

### 1.1 Build the mother/daughter/info maps (per event)

Every `GenParticle` is indexed; its mother and daughter indices are resolved by
**searching the candidate pointer vector** (`cands`). Hard-process particles
(`status 21–23`) go into `TreePar`; final-state / intermediate leptons
(`status 1 or 2`, `|pdgId| ∈ [11,16]`) go into `FinalPar`; tops and Ws encountered
at hard-process level are indexed in the `SelectedpdgId` map.

```cpp
GenParticleCollection::const_iterator itGenParBegin = genParticles->begin();

vector<const reco::Candidate *> cands;
for (auto itGenParIndex = genParticles->begin(); itGenParIndex != genParticles->end(); ++itGenParIndex)
    cands.push_back(&*itGenParIndex);

for (auto itGenPar = genParticles->begin(); itGenPar != genParticles->end(); itGenPar++)
{
    if(itGenPar->status() == 62){
        if(itGenPar->pdgId() ==  6) ssbtreeManager->Fill("GenTop",   itGenPar->pt(), itGenPar->eta(), itGenPar->phi(), itGenPar->energy(), 0);
        if(itGenPar->pdgId() == -6) ssbtreeManager->Fill("GenAnTop", itGenPar->pt(), itGenPar->eta(), itGenPar->phi(), itGenPar->energy(), 0);
    }
    int GenParIndex = itGenPar - itGenParBegin;
    OriginalMom.clear();
    for (unsigned int N_Mother = 0; N_Mother < itGenPar->numberOfMothers(); ++N_Mother)
        OriginalMom.push_back(find(cands.begin(), cands.end(), itGenPar->mother(N_Mother)) - cands.begin());
    OriginalDau.clear();
    for (unsigned int N_Daughter = 0; N_Daughter < itGenPar->numberOfDaughters(); ++N_Daughter)
        OriginalDau.push_back(find(cands.begin(), cands.end(), itGenPar->daughter(N_Daughter)) - cands.begin());

    AllParMom[GenParIndex] = OriginalMom;
    AllParDau[GenParIndex] = OriginalDau;

    pdgId_status.clear();
    pdgId_status.push_back(itGenPar->pdgId());
    pdgId_status.push_back(itGenPar->status());
    AllParInfo[GenParIndex] = pdgId_status;

    if ( (itGenPar->status() > 20 && itGenPar->status() < 24) ) {        // without proton
        TreePar.push_back(GenParIndex);
        if ( abs(itGenPar->pdgId()) == 6 || abs(itGenPar->pdgId()) == 24 )
            SelectedpdgId[itGenPar->pdgId()] = GenParIndex;             // save index of top and W
    }
    if ( (itGenPar->status() == 1 || itGenPar->status() == 2) &&
         (abs(itGenPar->pdgId()) > 10 && abs(itGenPar->pdgId()) < 17) )
        FinalPar.push_back(GenParIndex);                                // final-state + intermediate l/nu
}
```

> **Note A (two different tops).** `GenTop`/`GenAnTop` **kinematics** are filled
> from the `status() == 62` copy (post-FSR, the decaying top). The top that
> anchors the 12-slot family tree (`SelectedpdgId[6]`, slot 2) is the
> `status 21–23` **hard-process** copy. In MiniAOD these are *different copies of
> the same top*, so `GenTop_pt != GenPar_pt[t]` in general.

### 1.2 isSignal

```cpp
if (SelectedpdgId.find(6) != SelectedpdgId.end() && SelectedpdgId.find(-6) != SelectedpdgId.end())
    isSignal = true;
```

ttbar signal ⇔ both `t` and `t̄` were found at hard-process level.

### 1.3 Signal branch — the 12-slot `SelectedPar`

```cpp
if ( isSignal == true ) {
    for (unsigned int SelectedB = 0; SelectedB < TreePar.size(); ++SelectedB) {
        if ( abs(AllParInfo[TreePar.at(SelectedB)].at(0)) == 5 &&
             abs(AllParInfo[AllParMom[TreePar.at(SelectedB)].at(0)].at(0)) == 6)
            SelectedpdgId[AllParInfo[TreePar.at(SelectedB)].at(0)] = TreePar.at(SelectedB);   // b from top
    }

    for (unsigned int FinaltoTree = 0; FinaltoTree < FinalPar.size(); ++FinaltoTree){
        if ( abs( AllParInfo[AllParMom[FinalPar.at(FinaltoTree)].at(0)].at(0) ) == 24){       // mother is W
            TreePar.push_back(FinalPar.at(FinaltoTree));
            FinalPar.erase(find(FinalPar.begin(), FinalPar.end(), FinalPar.at(FinaltoTree)));
            --FinaltoTree;
        }
    }                                                                    // move W-decay finals into TreePar

    SelectedPar.push_back(0);                                            // slot 0  p+
    SelectedPar.push_back(1);                                            // slot 1  p+
    SelectedPar.push_back(SelectedpdgId[6]);                            // slot 2  t
    SelectedPar.push_back(SelectedpdgId[-6]);                           // slot 3  t̄
    SelectedPar.push_back(SelectedpdgId[24]);                           // slot 4  W+
    SelectedPar.push_back(SelectedpdgId[5]);                            // slot 5  b
    SelectedPar.push_back(SelectedpdgId[-24]);                          // slot 6  W-
    SelectedPar.push_back(SelectedpdgId[-5]);                           // slot 7  b̄

    TreePar.erase(find(TreePar.begin(), TreePar.end(), SelectedpdgId[6]));
    TreePar.erase(find(TreePar.begin(), TreePar.end(), SelectedpdgId[-6]));
    TreePar.erase(find(TreePar.begin(), TreePar.end(), SelectedpdgId[24]));
    TreePar.erase(find(TreePar.begin(), TreePar.end(), SelectedpdgId[-24]));
    TreePar.erase(find(TreePar.begin(), TreePar.end(), SelectedpdgId[5]));
    TreePar.erase(find(TreePar.begin(), TreePar.end(), SelectedpdgId[-5]));

    for (unsigned int RemoveLowIndex = 0; RemoveLowIndex < TreePar.size(); ++RemoveLowIndex) {
        if (TreePar.at(RemoveLowIndex) < 10) {                          // remove ttbar-mother gluons / p+ daughters
            TreePar.erase(find(TreePar.begin(), TreePar.end(), TreePar.at(RemoveLowIndex)));
            --RemoveLowIndex;
        }
    }

    int FromWplusSum = 0;
    for (unsigned int FromWplus = 0; FromWplus < TreePar.size(); ++FromWplus){
        if (FromWplusSum == 2) break;
        if (IndexLinker(AllParDau, SelectedpdgId[24], 0, TreePar.at(FromWplus)) != -1) {
            SelectedPar.push_back(TreePar.at(FromWplus));               // slots 8,9  W+ daughters
            TreePar.erase(find(TreePar.begin(), TreePar.end(), TreePar.at(FromWplus)));
            --FromWplus; ++FromWplusSum;
        }
    }

    for (unsigned int FromWminus = 0; FromWminus < TreePar.size(); ++FromWminus){
        //if (IndexLinker(AllParDau, SelectedpdgId[-24], 0, TreePar.at(FromWminus)) != -1) {   // <-- CHECK COMMENTED OUT
            SelectedPar.push_back(TreePar.at(FromWminus));             // slots 10,11  W- daughters (= leftovers)
        //}
    }
    // SelectedPar layout: {p+, p+, t, t̄, W+, b, W-, b̄, W+d1, W+d2, W-d1, W-d2}
    //                       0   1   2  3   4   5  6   7   8     9     10    11
```

> **Note B (W⁻ daughter asymmetry).** W⁺ daughters are selected by an explicit
> `IndexLinker` descendant test, taking exactly two. W⁻ daughters are **whatever
> remains** in `TreePar` — the `IndexLinker` guard is commented out. This relies
> on nothing but W⁻ daughters being left at this point.

> **Note C (missing particles become index 0).** `SelectedpdgId` is a
> `std::map<int,int>`; `SelectedpdgId[5]` for an absent key **inserts 0 and
> returns 0**, i.e. a missing b/W silently becomes *GenPart index 0* (a beam
> proton), not a flagged gap. The size of `SelectedPar` therefore stays at 8 for
> slots 0–7 regardless, and only the W-daughter count (slots 8–11) can make it
> `!= 12`.

### 1.4 ⚠️ The only malformed-selection signal: `SelectedPar.size() != 12`

```cpp
    if (SelectedPar.size() != 12) {
        cerr << "!!!!! Signal Sample : SelectedPar Error !!!!!" << endl;
        cout << "!!!!! Signal Sample : SelectedPar Error !!!!!" << endl;
        cout << endl << "SelectedPar : " << endl;
        for (unsigned int i = 0; i < SelectedPar.size(); ++i) cout << ParName[AllParInfo[SelectedPar.at(i)].at(0)] << " ";
        cout << endl;
        for (unsigned int i = 0; i < SelectedPar.size(); ++i) cout << SelectedPar.at(i) << " ";
        cout << endl;
    }
```

> **This is the crux of the all-hadronic question.** When the 12-slot build is
> incomplete the code **prints an error and then continues anyway** — it does NOT
> substitute a sentinel and does NOT skip the event. Whatever `Channel_Idx` falls
> out of the (short) `SelectedPar` is still written. There is **no `-999`** here
> or anywhere downstream.

### 1.5 `FillGenPar()` — per-slot family-tree record

```cpp
void SSBAnalyzer::FillGenPar(int GenIndex, int FirstMother, int SecondMother,
                             int FirstDaughter, int SecondDaughter,
                             GenParticleCollection::const_iterator itGenParFill,
                             SSBTreeManager* ssbtreeManager){
    itGenParFill += GenIndex;
    int nMo = 2, nDa = 2;
    if (FirstMother == -1) { --nMo; if (SecondMother == -1) --nMo; else FirstMother = SecondMother; }
    else if (SecondMother == -1) { --nMo; SecondMother = FirstMother; }
    else if (FirstMother == SecondMother) --nMo;
    if (FirstDaughter == -1) { --nDa; if (SecondDaughter == -1) --nDa; else FirstDaughter = SecondDaughter; }
    else if (SecondDaughter == -1) { --nDa; SecondDaughter = FirstDaughter; }
    else if (FirstDaughter == SecondDaughter) --nDa;

    ssbtreeManager->Fill("GenPar_Idx",        GenIndex);
    ssbtreeManager->Fill("GenPar_pdgId",      itGenParFill->pdgId());
    ssbtreeManager->Fill("GenPar_Status",     itGenParFill->status());
    ssbtreeManager->Fill("GenPar_Mom1_Idx",   FirstMother);
    ssbtreeManager->Fill("GenPar_Mom2_Idx",   SecondMother);
    ssbtreeManager->Fill("GenPar_Mom_Counter",nMo);
    ssbtreeManager->Fill("GenPar_Dau1_Idx",   FirstDaughter);
    ssbtreeManager->Fill("GenPar_Dau2_Idx",   SecondDaughter);
    ssbtreeManager->Fill("GenPar_Dau_Counter",nDa);
    ssbtreeManager->Fill("GenPar", itGenParFill->pt(), itGenParFill->eta(), itGenParFill->phi(), itGenParFill->energy(), genPar_index);
    genPar_index++;
}
```

The fixed mother/daughter wiring for the 12 signal slots is supplied by the caller:

```cpp
FillGenPar(SelectedPar.at(0), -1,-1, SelectedPar.at(2), SelectedPar.at(3), ...);   // p+
FillGenPar(SelectedPar.at(1), -1,-1, SelectedPar.at(2), SelectedPar.at(3), ...);   // p+
FillGenPar(SelectedPar.at(2), SelectedPar.at(0), SelectedPar.at(1), SelectedPar.at(4), SelectedPar.at(5), ...);  // t
FillGenPar(SelectedPar.at(3), SelectedPar.at(0), SelectedPar.at(1), SelectedPar.at(6), SelectedPar.at(7), ...);  // t̄
FillGenPar(SelectedPar.at(4), SelectedPar.at(2), -1, SelectedPar.at(8),  SelectedPar.at(9),  ...);  // W+
FillGenPar(SelectedPar.at(5), SelectedPar.at(2), -1, -1, -1, ...);                                   // b
FillGenPar(SelectedPar.at(6), SelectedPar.at(3), -1, SelectedPar.at(10), SelectedPar.at(11), ...);  // W-
FillGenPar(SelectedPar.at(7), SelectedPar.at(3), -1, -1, -1, ...);                                   // b̄
FillGenPar(SelectedPar.at(8..11), <W parent>, -1, -1, -1, ...);                                      // W daughters
```

### 1.6 Background branch (`else`)

```cpp
else {  // not ttbar
    SelectedPar.push_back(0); SelectedPar.push_back(1);
    for (unsigned int TreetoSel = 0; TreetoSel < TreePar.size(); ++TreetoSel){
        SelectedPar.push_back(TreePar.at(TreetoSel));
        TreePar.erase(find(TreePar.begin(), TreePar.end(), TreePar.at(TreetoSel))); --TreetoSel;
    }
    for (unsigned int FinaltoTree = 0; FinaltoTree < FinalPar.size(); ++FinaltoTree){
        int MompdgId = abs(AllParInfo[AllParMom[FinalPar.at(FinaltoTree)].at(0)].at(0));
        if ( MompdgId == 6 || MompdgId == 23 || MompdgId == 24 || MompdgId == 25 ){   // top/Z/W/H mother
            TreePar.push_back(FinalPar.at(FinaltoTree));
            FinalPar.erase(find(FinalPar.begin(), FinalPar.end(), FinalPar.at(FinaltoTree))); --FinaltoTree;
        }
    }
    for (unsigned int TreetoSel = 0; TreetoSel < TreePar.size(); ++TreetoSel){
        for (unsigned int SelectedSize = 0; SelectedSize < SelectedPar.size(); ++SelectedSize){
            int SelectedpdgId = abs(AllParInfo[SelectedPar.at(SelectedSize)].at(0));
            if ( SelectedpdgId == 6 || SelectedpdgId == 23 || SelectedpdgId == 24 || SelectedpdgId == 25 ) {
                if (IndexLinker(AllParMom, TreePar.at(TreetoSel), 0, SelectedPar.at(SelectedSize)) != -1 ) {
                    SelectedPar.push_back(TreePar.at(TreetoSel));
                    TreePar.erase(find(TreePar.begin(), TreePar.end(), TreePar.at(TreetoSel))); --TreetoSel; break;
                }
            }
        }
    }
    // ... FillGenPar over the whole variable-length SelectedPar ...
}
```

> **Note D (background still gets a channel).** The channel loop in §2.1 runs over
> this `SelectedPar` too, so a background event with a leptonic boson decay yields
> a **non-zero** `Channel_Idx`. Background is **not** forced to 0.

---

## 2. Channel computation

### 2.1 Direct channel `Channel_Idx` (and lepton count)

```cpp
int ChannelLepton = 0, ChannelLeptonFinal = 0, ChannelIndex = 0, ChannelIndexFinal = 0;
for (unsigned int OnlyLepton = 0; OnlyLepton < SelectedPar.size(); ++OnlyLepton) {
    int Lepton_pdgId = abs(AllParInfo[SelectedPar.at(OnlyLepton)].at(0));
    if (Lepton_pdgId == 11 || Lepton_pdgId == 13 || Lepton_pdgId == 15) {
        ++ChannelLepton;
        if (Lepton_pdgId == 15) ChannelIndex -= Lepton_pdgId;          // tau negated
        else                    ChannelIndex += Lepton_pdgId;
        SelectedDau.clear();
        if (Lepton_pdgId == 15) {                                       // collect tau finals for the FINAL channel
            for (unsigned int FinalCandidate = 0; FinalCandidate < FinalPar.size(); ++FinalCandidate)
                if (IndexLinker(AllParDau, SelectedPar.at(OnlyLepton), 0, FinalPar.at(FinalCandidate)) != -1)
                    SelectedDau.push_back(FinalPar.at(FinalCandidate));
        }
        SelParDau[SelectedPar.at(OnlyLepton)] = SelectedDau;
    }
}
```

> **The all-hadronic / failure behavior, precisely.** `ChannelIndex` starts at
> **0** and only moves when a lepton (`e/μ/τ`) is present among the selected
> particles. Therefore `Channel_Idx == 0` is produced by **three** distinct
> situations, all numerically identical:
> 1. genuine all-hadronic ttbar (slots 8–11 are four quarks),
> 2. an incomplete 12-slot build (slots 8–11 absent → no leptons counted; §1.4
>    has already printed `SelectedPar Error`),
> 3. (background path) a fully hadronic boson decay.
>
> The code makes **no attempt** to separate (1) from (2); the only trace of (2)
> is the `cerr` from §1.4. **There is no `-999` sentinel** — folding failures into
> `0` is the original, intended behavior.

### 2.2 Final channel `Channel_Idx_Final` (τ → ℓ resolved)

```cpp
ChannelLeptonFinal = ChannelLepton;
ChannelIndexFinal  = ChannelIndex;
for (map_i_it FinaltoSel = SelParDau.begin(); FinaltoSel != SelParDau.end(); ++FinaltoSel) {
    int Lepton_Mom_pdgId = 0, Lepton_Dau_pdgId = 0, Lepton_Mom_flag = 0;
    for (unsigned int DauIndex = 0; DauIndex < (FinaltoSel->second).size(); ++DauIndex) {
        if(SelectedPar.end() == find(SelectedPar.begin(), SelectedPar.end(), (FinaltoSel->second).at(DauIndex))) {
            SelectedPar.push_back((FinaltoSel->second).at(DauIndex));
            Lepton_Mom_pdgId = abs(AllParInfo[FinaltoSel->first].at(0));
            Lepton_Dau_pdgId = abs(AllParInfo[(FinaltoSel->second).at(DauIndex)].at(0));
            if (Lepton_Mom_pdgId != Lepton_Dau_pdgId) {                 // tau decayed to something
                if (Lepton_Mom_flag == 0) {                             // remove the tau once
                    ++Lepton_Mom_flag; --ChannelLeptonFinal;
                    if (Lepton_Mom_pdgId < 14) ChannelIndexFinal -= Lepton_Mom_pdgId;
                    if (Lepton_Mom_pdgId > 14) ChannelIndexFinal += Lepton_Mom_pdgId;
                }
                if (Lepton_Dau_pdgId == 11 || Lepton_Dau_pdgId == 13 || Lepton_Dau_pdgId == 15) {
                    FillGenPar((FinaltoSel->second).at(DauIndex), FinaltoSel->first, -1, -1, -1, ...);
                    ++ChannelLeptonFinal;
                    if (Lepton_Dau_pdgId < 14) ChannelIndexFinal += Lepton_Dau_pdgId;
                    if (Lepton_Dau_pdgId > 14) ChannelIndexFinal -= Lepton_Dau_pdgId;
                }
            }
        }
    }
}
```

The FINAL channel walks each selected `τ` down to its leptonic daughter (via
`IndexLinker` on the gen-daughter map) and rewrites the channel code accordingly.

### 2.3 Channel jets `Channel_Jets` / `Channel_Jets_Abs`

```cpp
int ChannelJets = 0, ChannelJetsAbs = 0;
if ( isSignal == true ) {
    for (unsigned int WIndex = 0; WIndex < 2; ++WIndex) {
        int Channel_pdgId = 0;
        unsigned int First_Dau_pdgId  = abs(AllParInfo[SelectedPar.at(2*WIndex+8)].at(0));
        unsigned int Second_Dau_pdgId = abs(AllParInfo[SelectedPar.at(2*WIndex+9)].at(0));
        if ( First_Dau_pdgId < 10 ) {
            if ( First_Dau_pdgId%2 == WIndex ) Channel_pdgId = 10*First_Dau_pdgId + Second_Dau_pdgId;
            else                               Channel_pdgId = First_Dau_pdgId + 10*Second_Dau_pdgId;
            if ( ChannelJets == 0 ) ChannelJets = Channel_pdgId;
            else                    ChannelJets = 100*ChannelJets + Channel_pdgId;
        }
    }
}
if ( ChannelJets > 0 ) {
    ChannelJetsAbs = ChannelJets;
    if ( (ChannelJetsAbs/10)%10 > ChannelJetsAbs%10 )   ChannelJetsAbs = 100*(ChannelJetsAbs/100) + 10*(ChannelJetsAbs%10) + (ChannelJetsAbs/10)%10;
    if ( ChannelJetsAbs/1000 > (ChannelJetsAbs/100)%10 ) ChannelJetsAbs = 1000*((ChannelJetsAbs/100)%10) + 100*(ChannelJetsAbs/1000) + (ChannelJetsAbs%100);
    if ( ChannelJetsAbs/100 > ChannelJetsAbs%100 )      ChannelJetsAbs = 100*(ChannelJetsAbs%100) + ChannelJetsAbs/100;
}

ssbtreeManager->Fill("GenPar_Count",               genPar_index);
ssbtreeManager->Fill("Channel_Idx",                ChannelIndex);
ssbtreeManager->Fill("Channel_Idx_Final",          ChannelIndexFinal);
ssbtreeManager->Fill("Channel_Jets",               ChannelJets);
ssbtreeManager->Fill("Channel_Jets_Abs",           ChannelJetsAbs);
ssbtreeManager->Fill("Channel_Lepton_Count",       ChannelLepton);
ssbtreeManager->Fill("Channel_Lepton_Count_Final", ChannelLeptonFinal);
```

---

## 3. `GenJet()`

```cpp
void SSBAnalyzer::GenJet(const edm::Event& iEvent, SSBTreeManager* ssbtreeManager) {
    edm::Handle<GenJetCollection> genJets;
    iEvent.getByToken(genJetInfoTag, genJets);
    genJet_index = 0;
    for (auto itgJet = genJets->begin(); itgJet != genJets->end(); itgJet++) {
        ssbtreeManager->Fill("GenJet", (*itgJet).pt(), (*itgJet).eta(), (*itgJet).phi(), (*itgJet).energy(), genJet_index);
        ssbtreeManager->Fill("GenJet_HCalEnergy", (*itgJet).hadEnergy());
        ssbtreeManager->Fill("GenJet_ECalEnergy", (*itgJet).emEnergy());
        genJet_index++;
    }
    ssbtreeManager->Fill("GenJet_Count", genJet_index);
}
```

> `hadEnergy()`/`emEnergy()` (HCal/ECal fractions) have **no NanoAOD equivalent**.

---

## 4. `GenMET()`

```cpp
void SSBAnalyzer::GenMET(const edm::Event& iEvent, SSBTreeManager* ssbtreeManager) {
    edm::Handle<GenMETCollection> genMETs;
    iEvent.getByToken(genMETInfoTag, genMETs);
    genMET_index = 0;
    for (auto itgMET = genMETs->begin(); itgMET != genMETs->end(); itgMET++) {
        ssbtreeManager->Fill("GenMET", (*itgMET).genMET()->pt(), 0, (*itgMET).genMET()->phi(), 0, genMET_index);
        genMET_index++;
    }
    ssbtreeManager->Fill("GenMET_Count", genMET_index);
}
```

---

## 5. Ghost B-hadron section (inside `analyze()`)

Uses the dedicated `matchGenBHadron`-style products. A b-hadron is kept only if it
maps to a reclustered gen-jet (`hadronJetId >= 0`); the **jet** kinematics go to
`GenBJet`, the **hadron** kinematics to `GenBHad`, plus the official
`FromTopWeakDecay` flag and signed `Flavour`.

```cpp
int num_genBjet = 0;
for(size_t hadronId = 0; hadronId < genBHadIndex->size(); ++hadronId) {
    const int hadronParticleId = genBHadIndex->at(hadronId);
    if(hadronParticleId < 0) continue;
    const int hadronJetId = genBHadJetIndex->at(hadronId);
    if(hadronJetId >= 0) {
        double jpt_  = genJetsReClus->at(hadronJetId).pt();
        double jeta_ = genJetsReClus->at(hadronJetId).eta();
        double jphi_ = genJetsReClus->at(hadronJetId).phi();
        double jenergy_ = genJetsReClus->at(hadronJetId).energy();
        ssbtreeManager->Fill("GenBJet", jpt_, jeta_, jphi_, jenergy_, num_genBjet);

        double gpt_  = genParBHad->at(genBHadIndex->at(hadronId)).pt();
        double geta_ = genParBHad->at(genBHadIndex->at(hadronId)).eta();
        double gphi_ = genParBHad->at(genBHadIndex->at(hadronId)).phi();
        double genergy_ = genParBHad->at(genBHadIndex->at(hadronId)).energy();
        ssbtreeManager->Fill("GenBHad", gpt_, geta_, gphi_, genergy_, num_genBjet);

        ssbtreeManager->Fill("GenBHad_FromTopWeakDecay", genBHadFromTopWeakDecay->at(hadronId));
        ssbtreeManager->Fill("GenBHad_Flavour",          genBHadFlavour->at(hadronId));
        num_genBjet++;
    }
}
ssbtreeManager->Fill("GenBJet_Count", num_genBjet);
ssbtreeManager->Fill("GenBHad_Count", num_genBjet);
```

> The b-hadron itself is identified by a dedicated CMSSW module (ghost
> reclustering); `FromTopWeakDecay` and `Flavour` come straight from that module's
> output collections — they are **not** recomputed here.

---

## 6. `IndexLinker()` — recursive ancestry/descendant walk

The workhorse used throughout `GenPar()`: given an index map (mother- or
daughter-direction) it recursively tests whether `target_index` is reachable from
`start_index`, optionally also matching pdgId/status/depth.

```cpp
int SSBAnalyzer::IndexLinker(map_i IndexMap, int start_index, int target_depth,
                             int target_index, int target_pdgid, int target_status,
                             bool PrintError, int LoopDepth){
    if ( ((start_index == target_index) || (target_index == -999)) &&
         ((AllParInfo[start_index].at(0) == target_pdgid) || (target_pdgid == 0)) &&
         ((AllParInfo[start_index].at(1) == target_status) || (target_status == 0)) ) {
        return start_index;
    }
    else {
        ++LoopDepth;
        int IndexLinkerResult = -1;
        for (unsigned int MapLoopIndex = 0; MapLoopIndex < IndexMap[start_index].size(); ++MapLoopIndex){
            if(IndexMap[start_index].at(MapLoopIndex) != -1) {
                IndexLinkerResult = IndexLinker(IndexMap, IndexMap[start_index].at(MapLoopIndex),
                                                target_depth, target_index, target_pdgid, target_status, PrintError, LoopDepth);
                if (IndexLinkerResult != -1){
                    if (LoopDepth == target_depth) return IndexMap[start_index].at(MapLoopIndex);
                    break;
                }
            }
        }
        return IndexLinkerResult;
    }
}
```

---

## 7. HERWIG branch (not reproduced in NanoAOD)

`GenPar()` has a second, structurally parallel branch for HERWIG samples
(`isHerwig`). Differences from PYTHIA: hard process is `status == 11`; beam
protons (`|pdgId| == 2212`, no mothers) are pushed as slots 0/1; an extra
"de-duplication" loop strips radiation copies of `t`/`W` before the same 12-slot
assembly and the **identical** channel computation run. Because NanoAOD's
`GenPart_statusFlags` (`isHardProcess`, `isLastCopy`) carry a **hadronizer-
independent** meaning, the NanoAOD port collapses both branches into one — so the
HERWIG path has no separate reproduction. See `docs/GenPart_channel_definition.md`
in the TopCPVCategorizer package for the statusFlags rationale.
