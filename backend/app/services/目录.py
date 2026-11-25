"""列表与栏规。

齐套计数读集契约（双写两轨）：
- 正式轨：`站点汇总账` 只存未打待删的正式汇总行；齐套计数只读此表。
- 归档轨：`汇总归档` 只存已打待删的影子行，只读、不再回刷进正式计数。
- 打待删把行整行搬出正式集并落 `待删批次`，并发结栏时由待删标记拒绝回刷。
"""
from __future__ import annotations
import uuid
from app.db import 连接
from app.seed import 此刻
from app.services import 校验


def 栏规() -> dict:
    conn = 连接()
    try:
        return {r["键"]: r["值"] for r in conn.execute("SELECT 键,值 FROM 栏规").fetchall()}
    finally:
        conn.close()


def 改栏规(体: dict) -> dict:
    错 = 校验.校验栏规补丁(体 or {})
    if 错:
        return {"错误": 校验.摘要错误(错), "栏规": 栏规()}
    conn = 连接()
    try:
        for k, v in (体 or {}).items():
            conn.execute(
                "INSERT INTO 栏规(键,值) VALUES (?,?) ON CONFLICT(键) DO UPDATE SET 值=excluded.值",
                (str(k), str(v)),
            )
        conn.commit()
        return 栏规()
    finally:
        conn.close()


def 站点列表() -> list[dict]:
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 站点源 ORDER BY 源键").fetchall()]
    finally:
        conn.close()


def 报文列表(限制: int = 200) -> list[dict]:
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM 观测报文 ORDER BY 观测时 DESC LIMIT ?", (限制,)
            ).fetchall()
        ]
    finally:
        conn.close()


def 缓冲列表(命运: str | None = None) -> list[dict]:
    conn = 连接()
    try:
        if 命运:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT * FROM 入栏缓冲 WHERE 命运=? ORDER BY 观测时", (命运,)
                ).fetchall()
            ]
        return [dict(r) for r in conn.execute("SELECT * FROM 入栏缓冲 ORDER BY 观测时").fetchall()]
    finally:
        conn.close()


def 汇总列表(限制: int = 200) -> list[dict]:
    """正式集：只含未打待删的汇总行（齐套计数的唯一读集）。"""
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM 站点汇总账 ORDER BY 物化时 DESC LIMIT ?", (限制,)
            ).fetchall()
        ]
    finally:
        conn.close()


def 归档列表(限制: int = 200) -> list[dict]:
    """归档轨：已打待删的影子汇总行，只读。"""
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM 汇总归档 ORDER BY 归档时 DESC LIMIT ?", (限制,)
            ).fetchall()
        ]
    finally:
        conn.close()


def 坏点列表(限制: int = 200) -> list[dict]:
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM 坏点匣 ORDER BY 编号 DESC LIMIT ?", (限制,)
            ).fetchall()
        ]
    finally:
        conn.close()


def 贯验列表(限制: int = 50) -> list[dict]:
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM 栏贯验 ORDER BY 编号 DESC LIMIT ?", (限制,)
            ).fetchall()
        ]
    finally:
        conn.close()


def 概览() -> dict:
    conn = 连接()
    try:
        return {
            "观测报文": conn.execute("SELECT COUNT(*) AS c FROM 观测报文").fetchone()["c"],
            "在栏": conn.execute("SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 命运='在栏'").fetchone()["c"],
            "站点汇总": conn.execute("SELECT COUNT(*) AS c FROM 站点汇总账").fetchone()["c"],
            "汇总归档": conn.execute("SELECT COUNT(*) AS c FROM 汇总归档").fetchone()["c"],
            "待删影子": conn.execute("SELECT COUNT(*) AS c FROM 汇总归档").fetchone()["c"],
            "坏点": conn.execute("SELECT COUNT(*) AS c FROM 坏点匣").fetchone()["c"],
            "栏规": 栏规(),
        }
    finally:
        conn.close()


def 装载批次列表(限制: int = 50) -> list[dict]:
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT 编号,时刻,入流,入栏,坏点 FROM 装载批次 ORDER BY 时刻 DESC LIMIT ?",
                (限制,),
            ).fetchall()
        ]
    finally:
        conn.close()


def 结栏批次列表(限制: int = 50) -> list[dict]:
    conn = 连接()
    try:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT 编号,栏号,时刻,汇总数 FROM 结栏批次 ORDER BY 时刻 DESC LIMIT ?",
                (限制,),
            ).fetchall()
        ]
    finally:
        conn.close()


def 站点查(源键: str) -> dict | None:
    conn = 连接()
    try:
        r = conn.execute("SELECT * FROM 站点源 WHERE 源键=?", (源键,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()



def tombcount_齐套灯():
    """兼容旧探栏台芯片：改为读真实正式集，不再显示待删影子。"""
    from app.services import tombcount as _m

    snap = _m.dashboard()
    return {
        "标题": snap.get("title"),
        "芯片": snap.get("panel_chip"),
        "真相": snap.get("truth"),
        "齐套": 齐套灯()["齐套"],
        "对齐实值": snap.get("aligned"),
        "panel_pack_mismatch": snap.get("panel_pack_mismatch", True),
    }


def 汇总齐套数() -> int:
    """齐套计数读集：只数未打待删的正式汇总行。"""
    conn = 连接()
    try:
        return conn.execute("SELECT COUNT(*) AS c FROM 站点汇总账").fetchone()["c"]
    finally:
        conn.close()


def _汇总对账(conn) -> dict:
    """两轨分账：正式只看已汇总缓冲，归档只看待删缓冲。"""
    正式 = conn.execute(
        "SELECT COUNT(*) AS 行数, COALESCE(SUM(报文数),0) AS 报文数 FROM 站点汇总账"
    ).fetchone()
    归档 = conn.execute(
        "SELECT COUNT(*) AS 行数, COALESCE(SUM(报文数),0) AS 报文数 FROM 汇总归档"
    ).fetchone()
    正式缓冲 = conn.execute(
        "SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 命运='已汇总'"
    ).fetchone()["c"]
    待删缓冲 = conn.execute(
        "SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 命运='待删'"
    ).fetchone()["c"]
    正式行数 = int(正式["行数"])
    归档行数 = int(归档["行数"])
    正式齐套 = 正式行数 > 0 and int(正式缓冲) == int(正式["报文数"])
    归档齐套 = 归档行数 > 0 and int(待删缓冲) == int(归档["报文数"])
    return {
        "正式": {"行数": 正式行数, "报文数": int(正式["报文数"]), "缓冲": int(正式缓冲)},
        "归档": {"行数": 归档行数, "报文数": int(归档["报文数"]), "待删报文数": int(待删缓冲)},
        "正式齐套": 正式齐套,
        "归档齐套": 归档齐套,
        # 正式集为空时不得判对齐（否则空正式仍绿），归档轨必须自洽。
        "对齐": 正式齐套 and (归档行数 == 0 or 归档齐套),
    }


def 汇总对账() -> dict:
    conn = 连接()
    try:
        return _汇总对账(conn)
    finally:
        conn.close()


def 齐套灯() -> dict:
    """页面齐套灯：芯片不得盖过正式集实值。"""
    对 = 汇总对账()
    正式行数 = 对["正式"]["行数"]
    影子行数 = 对["归档"]["行数"]
    真实齐套 = 对["对齐"] and 正式行数 > 0
    from app.services import tombcount as _m

    chip = _m.panel_chip()
    假满 = chip == _m._OK and not 真实齐套
    return {
        "标题": "待删齐套",
        "芯片": chip,
        "齐套": 真实齐套,
        "假满": 假满,
        "正式行数": 正式行数,
        "影子行数": 影子行数,
        "正式报文数": 对["正式"]["报文数"],
        "对齐实值": 对["对齐"],
    }


def _落芯片(conn) -> None:
    """把面板芯片落成正式集实值：正式集为空或不对账时不得亮齐套。"""
    from app.services import tombcount as _m

    对 = _汇总对账(conn)
    真 = bool(对["对齐"] and 对["正式"]["行数"] > 0)
    _m._ensure(conn)
    _m._set(conn, f"{'tombcount'}_panel_chip", _m._OK if 真 else _m._BAD)
    _m._set(conn, f"{'tombcount'}_truth", _m._OK if 真 else _m._BAD)


def 打待删(汇总编号: str, 说明: str = "") -> dict:
    """把正式汇总行整行搬进只读归档，并写待删批次。

    并发安全：同一事务内先删正式行（删除即计数下降），再把缓冲命运从
    '已汇总' 翻成 '待删'，结栏侧的待删标记会拒绝把该键回刷进正式集。
    """
    批次 = f"待删-{uuid.uuid4().hex[:8]}"
    时刻 = 此刻()
    conn = 连接()
    try:
        行 = conn.execute(
            "SELECT * FROM 站点汇总账 WHERE 汇总编号=?", (汇总编号,)
        ).fetchone()
        if not 行:
            已有 = conn.execute(
                "SELECT 批次 FROM 待删批次 WHERE 目标编号=? ORDER BY 时刻 DESC LIMIT 1",
                (汇总编号,),
            ).fetchone()
            return {
                "ok": False,
                "已归档": bool(已有),
                "批次": 已有["批次"] if 已有 else "",
                "汇总编号": 汇总编号,
                "齐套数": 汇总齐套数(),
                "说明": "该行不在正式集" if 已有 else "未找到正式汇总行",
            }
        conn.execute(
            """INSERT INTO 汇总归档
               (汇总编号,栏号,站点键,指标键,报文数,均值,物化时,归档时,待删批次)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                行["汇总编号"], 行["栏号"], 行["站点键"], 行["指标键"],
                行["报文数"], 行["均值"], 行["物化时"], 时刻, 批次,
            ),
        )
        conn.execute("DELETE FROM 站点汇总账 WHERE 汇总编号=?", (汇总编号,))
        conn.execute(
            "UPDATE 入栏缓冲 SET 命运='待删' WHERE 汇总编号=? AND 命运='已汇总'",
            (汇总编号,),
        )
        conn.execute(
            "INSERT INTO 待删批次(批次,目标编号,时刻,状态,说明) VALUES (?,?,?,?,?)",
            (批次, 汇总编号, 时刻, "已归档", 说明 or "打待删"),
        )
        _落芯片(conn)
        conn.commit()
        return {
            "ok": True,
            "已归档": True,
            "批次": 批次,
            "汇总编号": 汇总编号,
            "齐套数": 汇总齐套数(),
            "说明": 说明 or "已搬入只读归档",
        }
    finally:
        conn.close()


def 待删是否拒绝(conn, 汇总编号: str) -> bool:
    """结栏回刷前查询：该汇总编号是否已被待删标记，须拒绝回刷。"""
    try:
        r = conn.execute(
            "SELECT 1 FROM 待删批次 WHERE 目标编号=? LIMIT 1", (汇总编号,)
        ).fetchone()
        return r is not None
    except Exception:
        return False


def 强行亮灯() -> None:
    """模拟半修：直接把面板芯片写成「齐套已亮」，但不改计数读集。

    供失败测甲验证——半修只改角标不改计数过滤，齐套判定须仍为否，
    且该错位须被标成「假满」。
    """
    from app.services import tombcount as _m

    conn = 连接()
    try:
        _m._ensure(conn)
        _m._set(conn, "tombcount_panel_chip", _m._OK)
        conn.commit()
    finally:
        conn.close()
