"""Measure what a PiP screenshot shows, using the coordinate-encoded test video
(R = x/W*255, G = y/H*255, B = 128, white grid/text excluded by the B test).

Returns: visible source rect (x0,x1,y0,y1 in source px), screen-px-per-source-px
scale in X and Y (stretch = sx/sy), and black-bar coverage per edge."""
import numpy as np


def _fit(profile_idx, values):
    ok = ~np.isnan(values)
    if ok.sum() < 10:
        return None
    a, b = np.polyfit(profile_idx[ok], values[ok], 1)
    resid = values[ok] - (a * profile_idx[ok] + b)
    keep = np.abs(resid) < 6
    a, b = np.polyfit(profile_idx[ok][keep], values[ok][keep], 1)
    return a, b


def black_bars(arr, thr=14):
    """Fraction of near-black pixels in 3px bands along each edge."""
    blk = (arr[:, :, :3].max(axis=2) < thr)
    h, w = blk.shape
    band = 3
    return {
        "left": float(blk[:, :band].mean()), "right": float(blk[:, w - band:].mean()),
        "top": float(blk[:band, :].mean()), "bottom": float(blk[h - band:, :].mean()),
        "any_black_px": float(blk.mean()),
    }


def black_extent(arr, thr=14):
    """Width (px) of fully-black columns/rows on each side."""
    blk = (arr[:, :, :3].max(axis=2) < thr)
    colblack = blk.mean(axis=0) > 0.9
    rowblack = blk.mean(axis=1) > 0.9

    def run(v):
        n = 0
        for x in v:
            if not x:
                break
            n += 1
        return n
    return {"left": run(colblack), "right": run(colblack[::-1]),
            "top": run(rowblack), "bottom": run(rowblack[::-1])}


def edge_lines(arr):
    """Fraction of 'non-video' (dark) pixels on the outermost line of each side.
    Every video pixel has B=128, so max(R,G,B) >= ~115 inside the frame; a
    letterbox or a sub-pixel black seam shows up as dark pixels here."""
    lum = arr[:, :, :3].max(axis=2)
    d = lum < 110
    return {"left": round(float(d[:, 0].mean()), 3), "right": round(float(d[:, -1].mean()), 3),
            "top": round(float(d[0, :].mean()), 3), "bottom": round(float(d[-1, :].mean()), 3)}


def analyze(img, W, H, calib=None):
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w, _ = arr.shape
    R, G, B = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    valid = (np.abs(B - 128) < 28) & (arr.max(axis=2) > 14)
    Rm = np.where(valid, R, np.nan)
    Gm = np.where(valid, G, np.nan)
    with np.errstate(all="ignore"):
        col = np.nanmedian(Rm, axis=0)
        row = np.nanmedian(Gm, axis=1)
    fx = _fit(np.arange(w, dtype=np.float64), col.astype(np.float64))
    fy = _fit(np.arange(h, dtype=np.float64), row.astype(np.float64))
    # calibration maps decoded channel value -> true value (0..255): true = (v - c) / k
    kx, cx, ky, cy = (calib or (1.0, 0.0, 1.0, 0.0))
    res = {"size": [w, h], "black": black_bars(arr), "black_px": black_extent(arr), "edges": edge_lines(arr)}
    if fx and fy:
        ax, bx = fx
        ay, by = fy
        # value at pixel p: v = a*p + b ; true = (v-c)/k ; src = true/255*W
        def src_x(p):
            return ((ax * p + bx) - cx) / kx / 255.0 * W

        def src_y(p):
            return ((ay * p + by) - cy) / ky / 255.0 * H
        # edges of the window are pixel boundaries -0.5 and w-0.5
        x0, x1 = src_x(-0.5), src_x(w - 0.5)
        y0, y1 = src_y(-0.5), src_y(h - 0.5)
        sx = w / (x1 - x0)
        sy = h / (y1 - y0)
        res.update({"x0": round(x0, 1), "x1": round(x1, 1), "y0": round(y0, 1), "y1": round(y1, 1),
                    "src_w": round(x1 - x0, 1), "src_h": round(y1 - y0, 1),
                    "sx": round(sx, 4), "sy": round(sy, 4), "stretch": round(sx / sy, 4),
                    "fit": [ax, bx, ay, by]})
        g = grid_fit(arr, W, H, res)
        if "x" in g and "y" in g:
            gx, gy = g["x"], g["y"]
            res["grid"] = {"x0": round(gx["src0"], 1), "x1": round(gx["src1"], 1),
                           "y0": round(gy["src0"], 1), "y1": round(gy["src1"], 1),
                           "sx": round(gx["scale"], 4), "sy": round(gy["scale"], 4),
                           "stretch": round(gx["scale"] / gy["scale"], 4),
                           "lines": [gx["lines"], gy["lines"]]}
    return res


def _peaks(profile, min_prom=12.0):
    """Sub-pixel centers of bright ridges (grid lines) in a 1-D profile."""
    p = np.asarray(profile, dtype=np.float64)
    n = len(p)
    k = 9
    pad = np.pad(p, k, mode="edge")
    base = np.array([np.median(pad[i:i + 2 * k + 1]) for i in range(n)])
    ex = p - base
    out = []
    i = 0
    while i < n:
        if ex[i] > min_prom:
            j = i
            while j < n and ex[j] > min_prom * 0.35:
                j += 1
            lo = max(0, i - 1)
            seg = ex[lo:j + 1].clip(min=0)
            if seg.sum() > 0:
                out.append(float((np.arange(lo, lo + len(seg)) * seg).sum() / seg.sum()))
            i = j + 1
        else:
            i += 1
    return out


def grid_fit(arr, W, H, approx):
    """Refine mapping using the white grid lines at every 10% of the source.
    approx: dict with x0,x1,y0,y1 from the color fit (used to label lines)."""
    h, w, _ = arr.shape
    mn = arr[:, :, :3].min(axis=2)
    colp = np.median(mn, axis=0)
    rowp = np.median(mn, axis=1)
    res = {}
    for axis, prof, n, S, a0, a1 in (("x", colp, w, W, approx["x0"], approx["x1"]),
                                    ("y", rowp, h, H, approx["y0"], approx["y1"])):
        pk = _peaks(prof)
        pts = []
        for c in pk:
            src = a0 + (c + 0.5) / n * (a1 - a0)          # approximate source coord
            i = round(src / (S / 10))
            if 1 <= i <= 9 and abs(src - i * S / 10) < S / 40:
                pts.append((c, i * S / 10))
        # one peak per grid index: keep the strongest candidate (closest to prediction)
        best = {}
        for c, x in pts:
            pred = (x - a0) / (a1 - a0) * n - 0.5
            if x not in best or abs(c - pred) < abs(best[x] - pred):
                best[x] = c
        pts = [(c, x) for x, c in best.items()]
        if len(pts) >= 2:
            cs = np.array([p[0] for p in pts]); xs = np.array([p[1] for p in pts])
            s, o = np.polyfit(xs, cs, 1)                     # screen = s*src + o
            keep = np.abs(cs - (s * xs + o)) < 1.5
            if keep.sum() >= 2 and keep.sum() < len(cs):
                cs, xs = cs[keep], xs[keep]
                s, o = np.polyfit(xs, cs, 1)
            pts = list(zip(cs, xs))
            res[axis] = {"scale": float(s), "src0": float((-0.5 - o) / s),
                         "src1": float((n - 0.5 - o) / s), "lines": len(pts)}
    return res


def calibrate(img, W, H):
    """Use an uncropped, unletterboxed full-frame screenshot to calibrate the
    decoded color ramp (limited-range / matrix differences)."""
    r = analyze(img, W, H)
    ax, bx, ay, by = r["fit"]
    w, h = r["size"]
    # full frame: value at p=-0.5 corresponds to true 0, at p=w-0.5 to true 255
    v0x, v1x = ax * -0.5 + bx, ax * (w - 0.5) + bx
    v0y, v1y = ay * -0.5 + by, ay * (h - 0.5) + by
    return ((v1x - v0x) / 255.0, v0x, (v1y - v0y) / 255.0, v0y)


def verify(img, crop, W, H, tol=3.0):
    """Color-independent check: predict where the source grid lines (every 10%)
    must appear for this crop and window size, and match detected lines.
    Also fits the actual screen scale/offset from the matched lines."""
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    h, w, _ = arr.shape
    mn = arr[:, :, :3].min(axis=2)
    out = {"size": [w, h], "edges_dark": edge_lines(arr), "black_px": black_extent(arr), "black_bands": black_bands(arr)}
    for axis, prof, n, lo, hi in (("x", np.median(mn, axis=0), w, crop["l"], 1 - crop["r"]),
                                  ("y", np.median(mn, axis=1), h, crop["t"], 1 - crop["b"])):
        peaks = np.array(_peaks(prof))
        pred, got = [], []
        for i in range(1, 10):
            f = i / 10
            if lo < f < hi:
                p = (f - lo) / (hi - lo) * n - 0.5
                if 2 <= p <= n - 3:
                    pred.append((f, p))
        errs, pts = [], []
        for f, p in pred:
            if len(peaks):
                j = int(np.argmin(np.abs(peaks - p)))
                e = float(peaks[j] - p)
                if abs(e) <= tol:
                    errs.append(e)
                    pts.append((f, peaks[j]))
        r = {"expected_lines": len(pred), "matched": len(errs),
             "rms_px": round(float(np.sqrt(np.mean(np.square(errs)))), 2) if errs else None,
             "max_px": round(float(np.max(np.abs(errs))), 2) if errs else None}
        if len(pts) >= 2:
            fs = np.array([q[0] for q in pts]); cs = np.array([q[1] for q in pts])
            s, o = np.polyfit(fs, cs, 1)       # screen = s*frac + o
            S = W if axis == "x" else H
            r["scale"] = round(float(s / S), 4)                     # screen px per source px
            r["src0"] = round(float((-0.5 - o) / s * S), 1)
            r["src1"] = round(float((n - 0.5 - o) / s * S), 1)
        out[axis] = r
    if "scale" in out["x"] and "scale" in out["y"]:
        out["stretch"] = round(out["x"]["scale"] / out["y"]["scale"], 4)
    return out



def black_bands(arr, band=40, thr=14):
    """Widest run of (almost) fully black columns/rows within `band` px of each
    edge, wherever it starts: an overlay line on the very edge (like the
    modifier hint) must not hide a black strip behind it."""
    blk = (arr[:, :, :3].max(axis=2) < thr)
    col = blk.mean(axis=0) > 0.85
    row = blk.mean(axis=1) > 0.85

    def widest(v):
        best = cur = 0
        for x in v:
            cur = cur + 1 if x else 0
            best = max(best, cur)
        return best
    w, h = len(col), len(row)
    return {"left": widest(col[:band]), "right": widest(col[max(0, w - band):]),
            "top": widest(row[:band]), "bottom": widest(row[max(0, h - band):])}
