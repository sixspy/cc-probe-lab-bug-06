"""待删齐套双写两轨空壳：应归档旧档并改读新旗；当前只亮镜像芯片。"""
from __future__ import annotations

from app.db import 连接
from app.services import tombcount as core

_SLUG = "tombcount"
_TITLE = "待删齐套"
_OK = "齐套已亮"


def apply_dualwrite(note: str = "") -> dict:
    conn = 连接()
    try:
        core._ensure(conn)
        core._set(conn, f"{_SLUG}_dual_note", note or _TITLE)
        from app.services import 目录

        目录._落芯片(conn)
        conn.commit()
    finally:
        conn.close()
    return {
        "dual_chip": core.panel_chip(),
        "truth": core.truth_flag(),
        "active_read": core.active_read_ref(),
        "archive_count": len(core.archive_rows()),
        "live_flag": core.live_flag(),
    }


def dual_board() -> dict:
    apply_dualwrite()
    dash = core.dashboard()
    return {
        "dual_chip": core.panel_chip(),
        "truth": core.truth_flag(),
        "active_read": core.active_read_ref(),
        "archive": core.archive_rows(),
        "live_flag": core.live_flag(),
        "dash": dash,
        "fate": "dualwrite",
        "panel_pack_mismatch": dash.get("panel_chip") == core._OK and not dash.get("aligned"),
        "title": f"{_TITLE}双写面",
    }
