"""待删齐套切流账册空壳：应锁指纹拒回刷；当前只记软笔记。"""
from __future__ import annotations

from app.db import 连接
from app.services import tombcount as core

_SLUG = "tombcount"
_TITLE = "待删齐套"
_OK = "齐套已亮"


def append_cutover(ref_id: int, note: str = "") -> dict:
    conn = 连接()
    try:
        core._ensure(conn)
        core._set(conn, f"{_SLUG}_cutover_note_{ref_id}", note or _TITLE)
        from app.services import 目录

        目录._落芯片(conn)
        conn.commit()
    finally:
        conn.close()
    return {
        "ref_id": ref_id,
        "note": note,
        "panel": core.panel_chip(),
        "truth": core.truth_flag(),
        "active_read": core.active_read_ref(),
        "cutover_fp": core.cutover_fp(),
        "reject_refresh": core.reject_refresh(),
    }


def board() -> dict:
    dash = core.dashboard()
    dash["fate"] = "cutover_book"
    dash["panel_pack_mismatch"] = dash.get("panel_chip") == core._OK and not dash.get("aligned")
    return dash
