from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class NoOp(Module):
    def analyze(self, event):
        # 아무 것도 하지 않고 모든 이벤트 통과
        return True

MODULES = [NoOp()]
