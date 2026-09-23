"""Prints WM_NCHITTEST results across the edges of every open PiP window
(where Windows starts a resize)."""
import os, sys
HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "harness")
sys.path.insert(0, HARNESS)
import ctypes
from ctypes import wintypes
import winutil as W
u = W.user32
u.SendMessageW.restype = ctypes.c_ssize_t
u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
HT = {0:"NOWHERE",1:"CLIENT",2:"CAPTION",10:"LEFT",11:"RIGHT",12:"TOP",13:"TOPLEFT",14:"TOPRIGHT",15:"BOTTOM",16:"BOTTOMLEFT",17:"BOTTOMRIGHT",18:"BORDER",-1:"TRANSPARENT"}
pips = [x for x in W.windows() if x["cls"] == "MozillaDialogClass" and x["title"] == "Picture-in-Picture"]
for p in pips:
    h = p["hwnd"]; l, t, r, b = p["rect"]
    print("PiP hwnd", h, p["rect"])
    def ht(x, y):
        lp = ((y & 0xFFFF) << 16) | (x & 0xFFFF)
        v = u.SendMessageW(h, 0x84, 0, lp)
        fp = W.root_of(W.window_from_point(x, y))
        cls = ctypes.create_unicode_buffer(128); u.GetClassNameW(fp, cls, 128)
        return f"{HT.get(v, v)}{'' if fp == h else ' [topmost at point: ' + cls.value + ' ' + str(fp) + ']'}"
    cx, cy = (l + r) // 2, (t + b) // 2
    print(" top edge (center x):", [(d, ht(cx, t + d)) for d in (0, 2, 4, 6, 10, 15, 16, 20, 30)])
    print(" left edge (center y):", [(d, ht(l + d, cy)) for d in (0, 2, 6, 10, 15, 16, 20)])
    print(" bottom edge:", [(d, ht(cx, b - 1 - d)) for d in (0, 6, 15, 16)])
    print(" right edge:", [(d, ht(r - 1 - d, cy)) for d in (0, 6, 15, 16)])
    print(" top-left corner:", ht(l + 6, t + 6), " center:", ht(cx, cy))
