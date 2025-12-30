import uproot
import glob

# 파일 리스트 확보
files = glob.glob("*.root")

total_events = 0
for f in files:
    # 파일을 다 읽지 않고 메타데이터만 스캔하므로 매우 빠름
    with uproot.open(f) as file:
        total_events += file["Events"].num_entries

print(f"Total Events: {total_events}")
