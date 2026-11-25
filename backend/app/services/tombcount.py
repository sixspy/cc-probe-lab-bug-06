"""待删齐套收口面：齐套判定只读未删正式集，芯片随正式集落值。

历史字段（active_read/cutover_fp/live_flag/archive_*）保留为只读说明，
不再作为齐套判定依据；归档真相在 `站点汇总账/归档` 与 `汇总对账`。
"""
from __future__ import annotations

from app.db import 连接

_SLUG = "tombcount"
_OK = "齐套已亮"
_BAD = "待删仍计"
_TITLE = "待删齐套"
_OLD = "old_track"
_CUTOVER = "cutover_book"
_LIVE = "live_flag"


def _ensure(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS 探栏元("
        "键 TEXT PRIMARY KEY, 值 TEXT NOT NULL)"
    )


def _get(conn, key: str, default: str = "") -> str:
    _ensure(conn)
    r = conn.execute("SELECT 值 FROM 探栏元 WHERE 键=?", (key,)).fetchone()
    return r["值"] if r else default


def _set(conn, key: str, value: str) -> None:
    _ensure(conn)
    conn.execute(
        "INSERT INTO 探栏元(键,值) VALUES (?,?) "
        "ON CONFLICT(键) DO UPDATE SET 值=excluded.值",
        (key, value),
    )


def panel_chip() -> str:
    conn = 连接()
    try:
        return _get(conn, f"{_SLUG}_panel_chip", _OK)
    finally:
        conn.close()


def truth_flag() -> str:
    conn = 连接()
    try:
        return _get(conn, f"{_SLUG}_truth", _BAD)
    finally:
        conn.close()


def active_read_ref() -> str:
    conn = 连接()
    try:
        return _get(conn, f"{_SLUG}_active_read", _OLD)
    finally:
        conn.close()


def cutover_fp() -> str:
    conn = 连接()
    try:
        return _get(conn, f"{_SLUG}_cutover_fp", "stale-fp")
    finally:
        conn.close()


def reject_refresh() -> bool:
    conn = 连接()
    try:
        return _get(conn, f"{_SLUG}_reject_refresh", "0") == "1"
    finally:
        conn.close()


def live_flag() -> str:
    conn = 连接()
    try:
        return _get(conn, f"{_SLUG}_live_flag", "")
    finally:
        conn.close()


def archive_rows() -> list[dict]:
    """归档轨真相：读只读的 `汇总归档`（待删影子行）。"""
    conn = 连接()
    try:
        _ensure(conn)
        try:
            rows = conn.execute(
                "SELECT * FROM 汇总归档 ORDER BY 归档时"
            ).fetchall()
        except Exception:
            rows = []
        return [dict(r) for r in rows]
    finally:
        conn.close()


def paint_ok() -> str:
    """兼容旧接口：仅在正式集确实齐套时才点亮芯片，否则落真相值。"""
    from app.services import 目录

    conn = 连接()
    try:
        _ensure(conn)
        目录._落芯片(conn)
        conn.commit()
        return panel_chip()
    finally:
        conn.close()


def commit_action(payload: dict | None = None) -> dict:
    """记录动作；芯片随正式集落值，不得凭动作凭空点亮。"""
    payload = payload or {}
    conn = 连接()
    try:
        c = int(_get(conn, f"{_SLUG}_counter", "0") or "0") + 1
        _set(conn, f"{_SLUG}_counter", str(c))
        _set(conn, f"{_SLUG}_last_payload", str(payload)[:200])
        _set(conn, f"{_SLUG}_active_read", _CUTOVER if payload.get("commit") else _OLD)
        _ensure(conn)
        from app.services import 目录

        目录._落芯片(conn)
        conn.commit()
        snap = snapshot()
        return {
            "ok": True,
            "chip": snap["panel_chip"],
            "title": _TITLE,
            "counter": c,
            "active_read": snap["active_read"],
            "cutover_fp": snap["cutover_fp"],
            "reject_refresh": snap["reject_refresh"],
            "archive_count": snap["archive_count"],
            "live_flag": snap["live_flag"],
            "aligned": snap["aligned"],
            "message": f"{_TITLE}动作已记录，芯片按正式集判定",
        }
    finally:
        conn.close()


def half_fix_display() -> dict:
    paint_ok()
    return {
        "panel_chip": panel_chip(),
        "truth": truth_flag(),
        "active_read": active_read_ref(),
        "archive_count": len(archive_rows()),
        "half_fixed": True,
    }


def snapshot() -> dict:
    ref = active_read_ref()
    chip = panel_chip()
    truth = truth_flag()
    arch = archive_rows()
    # 面板对齐以正式集实值为准，不再以旧读轨/假指纹判定。
    from app.services import 目录

    real = 目录.汇总对账()
    real_ok = bool(real["对齐"] and real["正式"]["行数"] > 0)
    aligned = chip == _OK and truth == _OK and real_ok
    return {
        "title": _TITLE,
        "panel_chip": chip,
        "truth": truth,
        "active_read": ref,
        "cutover_fp": cutover_fp(),
        "reject_refresh": reject_refresh(),
        "archive_count": len(arch),
        "live_flag": live_flag(),
        "aligned": aligned,
        "panel_pack_mismatch": chip == _OK and not aligned,
        "gate_bypass": False,
        "正式行数": real["正式"]["行数"],
        "待删影子行数": real["归档"]["行数"],
    }


def dashboard() -> dict:
    snap = snapshot()
    return {
        **snap,
        "ok_chip": _OK,
        "bad_chip": _BAD,
        "label": _TITLE,
        "read_tracks": {
            "old_track": _OLD,
            "cutover_book": _CUTOVER,
            "live_flag": _LIVE,
        },
    }


def reconcile_display() -> dict:
    return half_fix_display()
