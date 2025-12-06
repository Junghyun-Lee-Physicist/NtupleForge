# NtupleForge

**NtupleForge** provides utilities for running NanoAOD post-processing without modifying the upstream `PhysicsTools/NanoAODTools` package directly.

- [Link to CMSSW NanoAODTools framework](https://github.com/cms-sw/cmssw/tree/CMSSW_14_2_X/PhysicsTools/NanoAODTools)

## 🛠️ Setup

1. Prepare a CMSSW area, check out the official NanoAOD tools, and clone `NtupleForge`.
   *(Note: `scram b` is required to compile and update python paths)*

   ```bash
   cmsrel CMSSW_14_2_1
   cd CMSSW_14_2_1/src
   cmsenv
   
   # Setup standard NanoAODTools
   git cms-init
   git cms-addpkg PhysicsTools/NanoAODTools
   
   # Clone NtupleForge
   git clone [https://github.com/Junghyun-Lee-Physicist/NtupleForge.git](https://github.com/Junghyun-Lee-Physicist/NtupleForge.git)
   
   # Compile to setup environment
   scram b -j 8
   cd NtupleForge
   ```
