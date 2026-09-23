"""Win32 helpers: DPI-aware window lookup, screen capture, idle detection and
real OS-level input (SendInput) for end-to-end gesture tests."""
import ctypes, time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")
user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2

from PIL import ImageGrab  # noqa: E402  (after DPI awareness)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def windows(pid=None, title_sub=None, visible=True):
    out = []

    def cb(h, l):
        if visible and not user32.IsWindowVisible(h):
            return True
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if pid is not None and p.value not in (pid if isinstance(pid, (set, list, tuple)) else {pid}):
            return True
        n = user32.GetWindowTextLengthW(h)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(h, buf, n + 1)
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls, 256)
        if title_sub and title_sub.lower() not in buf.value.lower():
            return True
        out.append({"hwnd": h, "title": buf.value, "cls": cls.value, "pid": p.value, "rect": rect(h)})
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return out


def rect(hwnd):
    """Visible frame bounds (DWM extended frame bounds), physical pixels: (l, t, r, b)."""
    r = wintypes.RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    if dwmapi.DwmGetWindowAttribute(wintypes.HWND(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS,
                                    ctypes.byref(r), ctypes.sizeof(r)) != 0:
        user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def window_rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def grab(box):
    return ImageGrab.grab(bbox=box, all_screens=True)


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def idle_ms():
    li = LASTINPUTINFO(ctypes.sizeof(LASTINPUTINFO), 0)
    user32.GetLastInputInfo(ctypes.byref(li))
    return ctypes.windll.kernel32.GetTickCount() - li.dwTime


def wait_idle(ms=3000, timeout=600):
    """Wait until the human has not touched mouse/keyboard for `ms`."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if idle_ms() >= ms:
            return True
        time.sleep(0.5)
    return False


# ---- SendInput -------------------------------------------------------------
INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
MOUSEEVENTF_MOVE, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x1, 0x2, 0x4
MOUSEEVENTF_ABSOLUTE, MOUSEEVENTF_VIRTUALDESK = 0x8000, 0x4000
KEYEVENTF_KEYUP = 0x2
VK_SHIFT, VK_LSHIFT = 0x10, 0xA0
ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def _send(*inputs):
    arr = (INPUT * len(inputs))(*inputs)
    n = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if n != len(inputs):
        raise OSError(ctypes.get_last_error(), "SendInput failed")


def _virt():
    SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
    g = user32.GetSystemMetrics
    return g(SM_XVIRTUALSCREEN), g(SM_YVIRTUALSCREEN), g(SM_CXVIRTUALSCREEN), g(SM_CYVIRTUALSCREEN)


def mouse_move(x, y):
    # SetCursorPos is exact in physical coords for a PMv2-aware process; follow
    # with a zero relative move so the input stream carries a WM_MOUSEMOVE.
    user32.SetCursorPos(int(x), int(y))
    i = INPUT(INPUT_MOUSE)
    i.u.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_MOVE, 0, 0)
    _send(i)


def mouse_button(down=True):
    i = INPUT(INPUT_MOUSE)
    i.u.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP, 0, 0)
    _send(i)


def key(vk, down=True):
    i = INPUT(INPUT_KEYBOARD)
    i.u.ki = KEYBDINPUT(vk, 0, 0 if down else KEYEVENTF_KEYUP, 0, 0)
    _send(i)


def cursor_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def window_from_point(x, y):
    return user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))


def root_of(hwnd):
    GA_ROOT = 2
    return user32.GetAncestor(hwnd, GA_ROOT)


def drag(x0, y0, x1, y1, steps=20, step_ms=12, shift=False, hold_ms=60):
    """Real OS drag from (x0,y0) to (x1,y1), optionally holding Shift.
    Returns True if a human moved the mouse meanwhile (cursor not where we put it)."""
    old = cursor_pos()
    foreign = False

    def move(x, y):
        nonlocal foreign
        mouse_move(x, y)
        time.sleep(0.004)
        if cursor_pos() != (int(x), int(y)):
            foreign = True
    try:
        if shift:
            key(VK_LSHIFT, True)
            time.sleep(0.05)
        move(x0, y0)
        time.sleep(0.08)
        move(x0 + 1, y0)   # a hover move so WM_NCHITTEST/SETCURSOR run
        time.sleep(0.05)
        move(x0, y0)
        time.sleep(0.05)
        if cursor_pos() != (int(x0), int(y0)):
            foreign = True
        mouse_button(True)
        time.sleep(hold_ms / 1000)
        for i in range(1, steps + 1):
            move(x0 + (x1 - x0) * i / steps, y0 + (y1 - y0) * i / steps)
            time.sleep(step_ms / 1000)
        time.sleep(0.08)
        mouse_button(False)
        time.sleep(0.05)
    finally:
        if shift:
            key(VK_LSHIFT, False)
        mouse_move(*old)
    return foreign


MonitorEnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)


def monitors():
    out = []
    def cb(hm, hdc, rc, l):
        r = rc.contents
        out.append((r.left, r.top, r.right, r.bottom))
        return True
    user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(cb), 0)
    return out


def primary_monitor():
    """(left, top, right, bottom) of the primary monitor, the one at (0, 0)."""
    for m in monitors():
        if m[0] <= 0 < m[2] and m[1] <= 0 < m[3]:
            return m
    return monitors()[0]


def print_window(hwnd):
    """Capture a window's own content (even if covered) via PrintWindow
    with PW_RENDERFULLCONTENT. Returns a PIL image in physical pixels."""
    from PIL import Image
    gdi32 = ctypes.WinDLL("gdi32")
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    hdc = user32.GetWindowDC(hwnd)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    ok = user32.PrintWindow(hwnd, mdc, 2)
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]
    bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = (ctypes.c_char * (w * h * 4))()
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp); gdi32.DeleteDC(mdc); user32.ReleaseDC(hwnd, hdc)
    return Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1).convert("RGB"), bool(ok)


def send_batch(events):
    """One SendInput call with several events: [('move', x, y) | ('up', 0, 0) | ('down', 0, 0)].
    Absolute moves use normalized virtual-desktop coordinates."""
    vx, vy, vw, vh = _virt()
    arr = []
    for kind, x, y in events:
        i = INPUT(INPUT_MOUSE)
        if kind == "move":
            nx = int(round((x - vx) * 65535 / (vw - 1)))
            ny = int(round((y - vy) * 65535 / (vh - 1)))
            i.u.mi = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, 0, 0)
        elif kind == "up":
            i.u.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, 0)
        else:
            i.u.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, 0)
        arr.append(i)
    _send(*arr)
