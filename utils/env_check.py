import os
import sys
import subprocess

class EnvChecker:
    def __init__(self):
        self.red = '\033[91m'
        self.green = '\033[92m'
        self.yellow = '\033[93m'
        self.reset = '\033[0m'

    def check_cmssw(self):
        """Checks if the CMSSW environment is set up."""
        cmssw_base = os.environ.get('CMSSW_BASE')
        if not cmssw_base:
            print(f"{self.red}[ERROR] CMSSW environment not set!{self.reset}")
            print(f"Please run 'cmsenv' in your release area.")
            sys.exit(1)
        else:
            print(f"{self.green}[INFO] CMSSW environment detected:{self.reset} {cmssw_base}")

    def check_proxy(self):
        """Checks if a valid VOMS proxy exists."""
        try:
            # Check using voms-proxy-info
            # -exists returns 0 if valid, 1 if not
            subprocess.check_call(['voms-proxy-info', '-exists'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Optional: Get timeleft
            timeleft = subprocess.check_output(['voms-proxy-info', '-timeleft']).decode().strip()
            print(f"{self.green}[INFO] VOMS Proxy detected.{self.reset} Time left: {int(timeleft)//3600}h {(int(timeleft)%3600)//60}m")
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"{self.yellow}[WARNING] No valid VOMS proxy found.{self.reset}")
            print(f"If you are reading files via XRootD (root://...), this script might fail.")
            print(f"Please run: {self.yellow}voms-proxy-init --voms cms --valid 168:00{self.reset}")
            # We do not exit here because local files might not need proxy
            
    def check_all(self):
        self.check_cmssw()
        self.check_proxy()

def validate_environment():
    checker = EnvChecker()
    checker.check_all()

if __name__ == "__main__":
    validate_environment()
