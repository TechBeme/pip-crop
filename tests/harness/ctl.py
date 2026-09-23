"""CLI to drive a long-running test browser.

  python ctl.py launch [librewolf|firefox] [port] [profile]   start browser (stays running)
  python ctl.py js <file.js|-> [port] [ctx]                   run JS (chrome ctx default), print JSON
  python ctl.py nav <url> [port]                              navigate current tab
  python ctl.py quit [port]
"""
import json, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mn

cmd = sys.argv[1]
if cmd == "launch":
    browser = sys.argv[2] if len(sys.argv) > 2 else "librewolf"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 2829
    prof = sys.argv[4] if len(sys.argv) > 4 else f"{browser}-{port}"
    extra = json.loads(sys.argv[5]) if len(sys.argv) > 5 else None
    m = mn.launch(browser, prof, port, extra_prefs=extra)
    caps = m.send("WebDriver:GetCapabilities") if False else None
    info = m.js("return {ua: navigator.userAgent, app: Services.appinfo.name, ver: Services.appinfo.version, pid: Services.appinfo.processID}")
    print(json.dumps({"launched": info, "profile": m.profile, "browser_pid": m.proc.pid}))
    m.sock.close()
elif cmd == "js":
    src = sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 2829
    ctx = sys.argv[4] if len(sys.argv) > 4 else "chrome"
    code = sys.stdin.read() if src == "-" else open(src, encoding="utf-8").read()
    m = mn.Marionette(port)
    m.start_session()
    try:
        wrapped = "return (async () => {\n" + code + "\n})();"
        print(json.dumps(m.js(wrapped, ctx=ctx), indent=1, ensure_ascii=False))
    finally:
        m.send("WebDriver:DeleteSession")
        m.sock.close()
elif cmd == "nav":
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 2829
    m = mn.Marionette(port)
    m.start_session()
    m.navigate(sys.argv[2])
    m.send("WebDriver:DeleteSession")
    m.sock.close()
elif cmd == "quit":
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 2829
    m = mn.Marionette(port)
    m.start_session()
    m.quit()
