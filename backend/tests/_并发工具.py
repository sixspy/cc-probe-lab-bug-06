"""并发压测工具：并发执行「打待删」与「结栏」，检查两轨一致、无假满。

被 test_tombcount_c.py 与 并发_打待删与结栏.py 共用。
本模块不初始化库；调用方负责先把 app.db 指向独立目录并 seed。
"""
from __future__ import annotations

import threading

_站 = "站-河东"
_指标 = "PM25"


def _批(前缀: str, 条数: int) -> dict:
    报文 = []
    for i in range(1, 条数 + 1):
        报文.append(
            {
                "报文编号": f"{前缀}-{i}",
                "站点键": _站,
                "指标键": _指标,
                "读数": 20 + i,
                "观测时": f"2026-11-24T09:{i:02d}:00Z",
            }
        )
    return {"批次编号": 前缀, "报文": 报文}


def _编号(明细) -> set[str]:
    return {x["汇总编号"] for x in (明细 or []) if x.get("汇总编号")}


def _校验一轮(轮: int, 已见: set[str], 错: list) -> None:
    from app.db import 连接
    from app.services import 目录, 贯验

    正式 = 目录.汇总列表()
    归档 = 目录.归档列表()
    正式号 = {x["汇总编号"] for x in 正式}
    归档号 = {x["汇总编号"] for x in 归档}

    共 = 正式号 & 归档号
    if 共:
        错.append(f"轮{轮}:两轨互窜 {sorted(共)}")
    if (正式号 | 归档号) != 已见:
        错.append(
            f"轮{轮}:汇总编号丢失或多余 见{len(已见)} 轨{len(正式号 | 归档号)}"
        )

    conn = 连接()
    try:
        for x in 正式:
            n = conn.execute(
                "SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 汇总编号=? AND 命运='已汇总'",
                (x["汇总编号"],),
            ).fetchone()["c"]
            if int(n) != int(x["报文数"]):
                错.append(
                    f"轮{轮}:正式轨{x['汇总编号']} 缓冲{n} != 报文数{x['报文数']}"
                )
        for x in 归档:
            n = conn.execute(
                "SELECT COUNT(*) AS c FROM 入栏缓冲 WHERE 汇总编号=? AND 命运='待删'",
                (x["汇总编号"],),
            ).fetchone()["c"]
            if int(n) != int(x["报文数"]):
                错.append(
                    f"轮{轮}:归档轨{x['汇总编号']} 待删缓冲{n} != 报文数{x['报文数']}"
                )
    finally:
        conn.close()

    对 = 贯验.水位对账()
    if 对["正式"]["行数"] == 0 and 对["对齐"]:
        错.append(f"轮{轮}:正式集为空仍判对齐（假满）")
    if 对["正式齐套"] and 目录.汇总齐套数() != 对["正式"]["行数"]:
        错.append(
            f"轮{轮}:齐套数{目录.汇总齐套数()} != 正式行数{对['正式']['行数']}"
        )

    灯 = 目录.齐套灯()
    if 灯["假满"]:
        错.append(f"轮{轮}:齐套灯假满")
    # 契约：正式集为空不得绿；影子行存在并不禁止绿（归档是只读、可共存）。
    if 灯["齐套"] and 灯["正式行数"] == 0:
        错.append(f"轮{轮}:空正式仍绿")
    if 灯["齐套"] != 对["正式齐套"]:
        错.append(f"轮{轮}:齐套灯与正式齐套不一致")


def run_race(轮数: int = 8, 每批: int = 2, 删光: bool = False) -> dict:
    """每轮：预结一次 → 并发（结栏 ∥ 打待删）→ 校验；可选删光剩余正式行。"""
    from app.services import 装载, 结栏, 目录

    错: list = []
    已见: set[str] = set()
    并发执行 = 0
    空正式轮 = 0
    空正式灯绿 = 0
    最终灯 = None

    for r in range(轮数):
        try:
            装载.装一批(_批(f"竞{r}a", 每批))
            预结 = 结栏.结当前栏()
            已见 |= _编号(预结.get("明细"))
        except Exception as e:  # 预结阶段异常直接记录
            错.append(f"轮{r}:预结异常 {e!r}")
            continue

        正式 = 目录.汇总列表()
        目标 = 正式[0]["汇总编号"] if 正式 else None

        try:
            装载.装一批(_批(f"竞{r}b", 每批))
        except Exception as e:
            错.append(f"轮{r}:二次装载异常 {e!r}")
            continue

        线程错: list = []
        关闭果: list = []
        栅栏 = threading.Barrier(2)

        def 收结栏() -> None:
            try:
                栅栏.wait(timeout=10)
                关闭果.append(结栏.结当前栏())
            except Exception as e:  # noqa: BLE001
                线程错.append(("结栏", repr(e)))

        def 打待删() -> None:
            try:
                栅栏.wait(timeout=10)
                if 目标:
                    目录.打待删(目标, "竞用")
            except Exception as e:  # noqa: BLE001
                线程错.append(("打待删", repr(e)))

        ta = threading.Thread(target=收结栏, name=f"结栏-{r}")
        tb = threading.Thread(target=打待删, name=f"打待删-{r}")
        ta.start()
        tb.start()
        ta.join(20)
        tb.join(20)
        if ta.is_alive() or tb.is_alive():
            错.append(f"轮{r}:并发超时（疑似锁死）")
        if 目标:
            并发执行 += 1
        for 关 in 关闭果:
            已见 |= _编号(关.get("明细"))
        if 线程错:
            错.append({"轮": r, "线程错": 线程错})

        if 删光:
            try:
                for 行 in list(目录.汇总列表()):
                    目录.打待删(行["汇总编号"], "竞用-删光")
            except Exception as e:  # noqa: BLE001
                错.append(f"轮{r}:删光异常 {e!r}")

        try:
            _校验一轮(r, 已见, 错)
            灯 = 目录.齐套灯()
            最终灯 = 灯
            if 灯["正式行数"] == 0:
                空正式轮 += 1
                if 灯["齐套"] or 灯["假满"]:
                    空正式灯绿 += 1
        except Exception as e:  # noqa: BLE001
            错.append(f"轮{r}:校验异常 {e!r}")

    return {
        "轮数": 轮数,
        "错": 错,
        "并发执行": 并发执行,
        "空正式轮": 空正式轮,
        "空正式灯绿": 空正式灯绿,
        "最终齐套灯": 最终灯,
    }
