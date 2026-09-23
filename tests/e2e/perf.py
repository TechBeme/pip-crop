"""CPU/GPU cost: native PiP vs native PiP + chrome crop vs canvas captureStream."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import json, subprocess, time
import psutil
import piptest as pip

MEASURE_S = 15


def lw_procs():
    return [p for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == "librewolf.exe"]


def cpu_seconds(procs):
    tot = 0.0
    for p in procs:
        try:
            c = p.cpu_times()
            tot += c.user + c.system
        except psutil.Error:
            pass
    return tot


def gpu_util(pids, seconds):
    ps = f"""
$ids = @({','.join(str(p) for p in pids)})
$c = Get-Counter '\\GPU Engine(*)\\Utilization Percentage' -SampleInterval 1 -MaxSamples {seconds} -ErrorAction SilentlyContinue
$agg = @{{}}
foreach ($s in $c) {{ foreach ($x in $s.CounterSamples) {{
  if ($x.InstanceName -match 'pid_(\\d+)_.*engtype_(.+)$') {{
    if ($ids -contains [int]$matches[1]) {{ $k = $matches[2]; if (-not $agg.ContainsKey($k)) {{ $agg[$k] = 0.0 }}; $agg[$k] += $x.CookedValue }}
  }} }} }}
$out = @{{}}; foreach ($k in $agg.Keys) {{ $out[$k] = [math]::Round($agg[$k] / {seconds}, 2) }}
$out | ConvertTo-Json -Compress
"""
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    try:
        return json.loads(r.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"err": r.stdout[-300:] + r.stderr[-300:]}


def measure(label):
    procs = lw_procs()
    pids = [p.pid for p in procs]
    c0, t0 = cpu_seconds(procs), time.time()
    g = gpu_util(pids, MEASURE_S)          # runs ~MEASURE_S seconds
    c1, t1 = cpu_seconds(procs), time.time()
    cpu = (c1 - c0) / (t1 - t0) * 100
    print(f"{label:34s} CPU {cpu:6.1f}% of one core ({len(procs)} processes) | GPU engines (sum %): {g}", flush=True)
    return {"label": label, "cpu_pct_one_core": round(cpu, 1), "gpu": g}


t = pip.T()
t.close_all()
results = []
t.m.navigate("http://127.0.0.1:8765/video.html?src=v169.mp4"); time.sleep(1.5)
pid = t.open_pip(wait=0.8)
t.player_call(pid, "setRect", {"x": 60, "y": 520, "w": 480, "h": 270})
time.sleep(5)
results.append(measure("1) native PiP, no crop"))
t.player_call(pid, "setCrop", {"l": 0.1, "r": 0.1, "t": 0.1, "b": 0.1})
time.sleep(5)
results.append(measure("2) native PiP + chrome crop"))
t.close_all()
# canvas pipeline (the architecture tested before): needs RFP canvas permission
t.chrome("""const pr = Services.scriptSecurityManager.createContentPrincipalFromOrigin("http://127.0.0.1:8765");
  Services.perms.addFromPrincipal(pr, "canvas", Services.perms.ALLOW_ACTION); return 1;""")
t.m.navigate("http://127.0.0.1:8765/canvas_crop.html?src=v169.mp4"); time.sleep(3)
t.content("window.__cropPiP.X(10); window.__cropPiP.video.focus(); await new Promise(r=>setTimeout(r,500)); return 1;")
pid2 = t.open_pip(wait=0.8)
t.player_call(pid2, "setRect", {"x": 60, "y": 520, "w": 384, "h": 270})
time.sleep(5)
fr0 = t.content("return window.__cropPiP.frames;")
results.append(measure("3) canvas drawImage+captureStream"))
fr1 = t.content("return [window.__cropPiP.frames, +(window.__cropPiP.drawMs / window.__cropPiP.frames).toFixed(3)];")
print(f"   canvas frames drawn during measurement: {fr1[0] - fr0} (~{(fr1[0] - fr0) / MEASURE_S:.0f}/s), mean drawImage {fr1[1]} ms")
t.close_all()
json.dump(results, open(os.path.join(pip.OUT, "perf.json"), "w"), indent=1)
t.close()
