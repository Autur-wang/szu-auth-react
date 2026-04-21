"""深大体育馆场地查询 + 并发抢预约

接口参数从 GymTicketGrabbing (Go) 项目逆向确认：

查询接口: POST /modules/sportVenue/getOpeningRoom.do
  请求: XMDM=001&YYRQ=2026-03-26&YYLX=1.0&KSSJ=18%3A00&JSSJ=19%3A00&XQDM=1
  响应: {"datas": {"getOpeningRoom": {"rows": [{"WID": "xxx", "CDMC": "羽毛球1号", "disabled": false}, ...]}}}

预约接口: POST /sportVenue/insertVenueBookingInfo.do
  请求: DHID=&YYRGH=学号&CYRS=&YYRXM=姓名&LXFS=手机号&CGDM=001&CDWID=场地WID
        &XMDM=001&XQWID=1&KYYSJD=18%3A00-19%3A00&YYRQ=2026-03-26&YYLX=1.0
        &YYKS=2026-03-26+18%3A00&YYJS=2026-03-26+19%3A00&PC_OR_PHONE=pc
  响应: {"code": "0", "msg": "成功"}

字段说明:
  XMDM = 项目代码（001=羽毛球）
  YYRQ = 预约日期
  YYLX = 预约类型（1.0=学生）
  KSSJ/JSSJ = 开始/结束时间
  XQDM/XQWID = 校区代码（1=粤海）
  YYRGH = 预约人工号（学号）
  YYRXM = 预约人姓名
  LXFS = 联系方式（手机号）
  CDWID = 场地唯一标识（WID）
  CGDM = 场馆代码（001）
  KYYSJD = 可预约时间段
  YYKS/YYJS = 预约开始/结束（日期+时间）
  PC_OR_PHONE = 终端类型
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy"


@dataclass
class Venue:
    """一个可预约的场地"""
    wid: str            # 场地唯一标识（WID）
    name: str           # 场地名称（CDMC，如"羽毛球1号"）
    venue_name: str     # 场馆名称（如"至快体育馆"）
    date: str           # 预约日期
    begin_hour: str     # 开始小时（如 "18"）
    end_hour: str       # 结束小时（如 "19"）
    sport_code: str     # 项目代码（如 "001"）
    campus_code: str    # 校区代码（如 "1"）

    @property
    def time_slot(self) -> str:
        return f"{self.begin_hour}:00-{self.end_hour}:00"

    @property
    def display(self) -> str:
        return f"{self.venue_name} {self.name} {self.time_slot}"


class BookingClient:
    """深大体育馆预约"""

    def __init__(
        self,
        session: requests.Session,
        username: str = "",
        real_name: str = "",
        phone: str = "",
    ):
        self.session = session
        self.username = username
        self.real_name = real_name
        self.phone = phone

        # Go 项目确认需要的请求头
        self.session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
        })

    # ─── 查询场地 ───────────────────────────────────────

    def query_venues(
        self,
        date: str,
        begin_hour: str,
        end_hour: str,
        sport_code: str = "001",
        campus_code: str = "1",
    ) -> List[Venue]:
        """
        查询指定时段的可预约场地。

        对应 Go 项目: GetOpenRooms()
        接口: POST /modules/sportVenue/getOpeningRoom.do
        """
        logger.info(f"查询: {date} {begin_hour}:00-{end_hour}:00")

        try:
            resp = self.session.post(
                f"{API_BASE}/modules/sportVenue/getOpeningRoom.do",
                data={
                    "XMDM": sport_code,          # 项目代码
                    "YYRQ": date,                 # 预约日期
                    "YYLX": "1.0",                # 预约类型（学生）
                    "KSSJ": f"{begin_hour}:00",   # 开始时间
                    "JSSJ": f"{end_hour}:00",     # 结束时间
                    "XQDM": campus_code,          # 校区
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f"查询请求失败: {e}")
            return []
        except ValueError:
            logger.error(f"查询返回非 JSON: {resp.text[:300]}")
            return []

        # 解析响应：datas → getOpeningRoom → rows
        try:
            rows = data["datas"]["getOpeningRoom"]["rows"]
        except (KeyError, TypeError):
            logger.warning(f"响应结构异常: {str(data)[:300]}")
            return []

        # 筛选未禁用的场地（disabled=false 即可预约）
        venues = []
        for item in rows:
            if not item.get("disabled", True):
                venues.append(Venue(
                    wid=item["WID"],
                    name=item.get("CDMC", "未知场地"),
                    venue_name=item.get("CGMC", item.get("CDMC", "未知场馆")),
                    date=date,
                    begin_hour=begin_hour,
                    end_hour=end_hour,
                    sport_code=sport_code,
                    campus_code=campus_code,
                ))

        logger.info(f"  → {len(venues)}/{len(rows)} 个可用")
        for v in venues[:5]:
            logger.debug(f"    {v.display} (WID={v.wid})")

        return venues

    def query_all_hours(
        self,
        date: str,
        hours: List[str],
        sport_code: str = "001",
        campus_code: str = "1",
    ) -> List[Venue]:
        """
        查询多个时段的所有可用场地。

        hours 格式: ["18-19", "19-20", "20-21"]
        """
        all_venues = []
        for hour_range in hours:
            parts = hour_range.split("-")
            if len(parts) != 2:
                logger.warning(f"时段格式错误: {hour_range}，应为 HH-HH")
                continue
            begin, end = parts
            venues = self.query_venues(date, begin, end, sport_code, campus_code)
            all_venues.extend(venues)
        return all_venues

    @staticmethod
    def filter_by_venue_names(venues: List[Venue], preferred_names: List[str]) -> List[Venue]:
        """
        按场馆名称偏好过滤和排序。

        preferred_names: ["至快体育馆", "至畅体育馆"]
        - 空列表 = 不过滤
        - 匹配的排前面，按偏好顺序；不匹配的排后面
        """
        if not preferred_names:
            return venues

        def sort_key(v: Venue) -> int:
            for i, name in enumerate(preferred_names):
                if name in v.venue_name or name in v.name:
                    return i
            return len(preferred_names)

        return sorted(venues, key=sort_key)

    # ─── 预约单个场地 ───────────────────────────────────

    def book_one(self, venue: Venue, max_retries: int = 5) -> bool:
        """
        预约单个场地，带重试。

        对应 Go 项目: AddOrderByInfo()
        接口: POST /sportVenue/insertVenueBookingInfo.do
        """
        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.post(
                    f"{API_BASE}/sportVenue/insertVenueBookingInfo.do",
                    data={
                        "DHID": "",
                        "YYRGH": self.username,                  # 学号
                        "CYRS": "",
                        "YYRXM": self.real_name,                 # 姓名
                        "LXFS": self.phone,                      # 手机号
                        "CGDM": venue.sport_code,                # 场馆代码
                        "CDWID": venue.wid,                      # 场地 WID
                        "XMDM": venue.sport_code,                # 项目代码
                        "XQWID": venue.campus_code,              # 校区
                        "KYYSJD": f"{venue.begin_hour}:00-{venue.end_hour}:00",
                        "YYRQ": venue.date,                      # 预约日期
                        "YYLX": "1.0",                           # 学生
                        "YYKS": f"{venue.date} {venue.begin_hour}:00",  # 开始
                        "YYJS": f"{venue.date} {venue.end_hour}:00",    # 结束
                        "PC_OR_PHONE": "pc",
                    },
                    timeout=5,
                )
                result = resp.json()

                code = str(result.get("code", ""))
                msg = result.get("msg", "")

                if code == "0" and msg == "成功":
                    logger.info(f"✅ 预约成功: {venue.name} {venue.time_slot}")
                    return True

                logger.warning(f"[{attempt}/{max_retries}] {venue.name}: {msg}")

                # 不可重试的错误
                if any(kw in msg for kw in ["已被预约", "已满", "已预约", "不可预约", "已过期", "超出"]):
                    return False

            except requests.RequestException as e:
                logger.warning(f"[{attempt}/{max_retries}] 请求异常: {e}")
            except ValueError:
                logger.warning(f"[{attempt}/{max_retries}] 返回非 JSON: {resp.text[:200]}")

            if attempt < max_retries:
                time.sleep(0.05 * attempt)

        return False

    # ─── 并发抢多个场地 ─────────────────────────────────

    def book_concurrent(
        self,
        venues: List[Venue],
        max_workers: int = 5,
        max_retries: int = 5,
    ) -> Optional[Venue]:
        """并发抢多个场地，一个成功就停。"""
        if not venues:
            logger.warning("没有可用场地")
            return None

        workers = min(max_workers, len(venues))
        logger.info(f"并发抢 {len(venues)} 个场地（{workers} 线程）...")

        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_venue = {
                pool.submit(self.book_one, v, max_retries): v
                for v in venues[:workers]
            }
            for future in as_completed(future_to_venue):
                venue = future_to_venue[future]
                try:
                    if future.result():
                        for f in future_to_venue:
                            f.cancel()
                        return venue
                except Exception as e:
                    logger.error(f"{venue.name} 异常: {e}")

        # 第一批没抢到，尝试剩余
        remaining = venues[workers:]
        if remaining:
            logger.info(f"尝试剩余 {len(remaining)} 个场地...")
            return self.book_concurrent(remaining, max_workers, max_retries)

        return None

    # ─── 预发抢票（核心优势）────────────────────────────

    def book_prefire(
        self,
        venues: List[Venue],
        open_time_str: str = "12:30:00",
        advance_ms: float = 100,
        burst_count: int = 10,
        burst_interval_ms: float = 20,
    ) -> Optional[Venue]:
        """
        预发抢票：在 12:30 前 advance_ms 毫秒开始密集发请求。

        原理：
          网络延迟 ~50-200ms，如果 12:29:59.900 发请求，
          到达服务器刚好 12:30:00.000，比等到 12:30 再发快了一个延迟。

        参数：
          venues: 要抢的场地列表
          open_time_str: 放票时间
          advance_ms: 提前多少毫秒开始发（根据测速结果设置）
          burst_count: 连发多少轮
          burst_interval_ms: 每轮间隔（毫秒）

        时间线：
          12:29:59.900  发第1轮（5个场地并发）  ─→ 飞行100ms ─→ 12:30:00.000 到达 ✅
          12:29:59.920  发第2轮                 ─→ 飞行100ms ─→ 12:30:00.020 到达 ✅
          ...
          12:30:00.080  发第10轮                ─→ 飞行100ms ─→ 12:30:00.180 到达 ✅
        """
        from datetime import datetime

        if not venues:
            logger.warning("没有可用场地")
            return None

        # 计算开火时间：12:30 前 advance_ms 毫秒
        today = datetime.now().strftime("%Y-%m-%d")
        target = datetime.strptime(f"{today} {open_time_str}", "%Y-%m-%d %H:%M:%S")
        advance_sec = advance_ms / 1000.0

        # 准备所有请求数据（提前构造，节省时间）
        payloads = []
        for v in venues:
            payloads.append((v, {
                "DHID": "",
                "YYRGH": self.username,
                "CYRS": "",
                "YYRXM": self.real_name,
                "LXFS": self.phone,
                "CGDM": v.sport_code,
                "CDWID": v.wid,
                "XMDM": v.sport_code,
                "XQWID": v.campus_code,
                "KYYSJD": f"{v.begin_hour}:00-{v.end_hour}:00",
                "YYRQ": v.date,
                "YYLX": "1.0",
                "YYKS": f"{v.date} {v.begin_hour}:00",
                "YYJS": f"{v.date} {v.end_hour}:00",
                "PC_OR_PHONE": "pc",
            }))

        url = f"{API_BASE}/sportVenue/insertVenueBookingInfo.do"

        logger.info(f"预发模式：提前 {advance_ms:.0f}ms，连发 {burst_count} 轮，"
                     f"间隔 {burst_interval_ms:.0f}ms")
        logger.info(f"目标场地 {len(venues)} 个，每轮并发 {len(venues)} 个请求")

        # 忙等到开火时间
        fire_time = target.timestamp() - advance_sec
        now = time.time()
        if now < fire_time - 2:
            time.sleep(fire_time - now - 2)
        while time.time() < fire_time:
            pass

        logger.info("🔥 开火！")

        # 连发多轮
        interval_sec = burst_interval_ms / 1000.0
        success_venue = None

        with ThreadPoolExecutor(max_workers=len(payloads)) as pool:
            for burst in range(burst_count):
                if success_venue:
                    break

                # 一轮：所有场地同时发
                futures = {
                    pool.submit(self._fire_one, url, data): venue
                    for venue, data in payloads
                }

                for future in as_completed(futures):
                    venue = futures[future]
                    try:
                        ok, msg = future.result()
                        if ok:
                            logger.info(f"✅ 第 {burst + 1} 轮抢到: {venue.display}")
                            success_venue = venue
                            break
                        # 场地已满，从下一轮移除
                        if any(kw in msg for kw in ["已被预约", "已满", "已预约"]):
                            payloads = [(v, d) for v, d in payloads if v.wid != venue.wid]
                    except Exception:
                        pass

                if not payloads:
                    logger.warning("所有场地都满了")
                    break

                # 下一轮间隔
                if not success_venue and burst < burst_count - 1:
                    time.sleep(interval_sec)

        elapsed = (time.time() - target.timestamp()) * 1000
        logger.info(f"预发结束，耗时 {elapsed:+.0f}ms（相对 12:30）")

        # 预发没抢到，降级到普通重试
        if not success_venue and payloads:
            logger.info("预发未命中，切换到普通重试...")
            remaining = [v for v, _ in payloads]
            success_venue = self.book_concurrent(remaining, max_workers=5, max_retries=10)

        return success_venue

    def _fire_one(self, url: str, data: dict) -> tuple:
        """发一个预约请求，返回 (成功?, 消息)"""
        try:
            resp = self.session.post(url, data=data, timeout=5)
            result = resp.json()
            code = str(result.get("code", ""))
            msg = result.get("msg", "")
            return (code == "0" and msg == "成功"), msg
        except Exception as e:
            return False, str(e)

    # ─── Cookie 验证 ────────────────────────────────────

    def validate_session(self) -> bool:
        """
        验证当前 session 是否有效（能访问查询接口）。

        对应 Go 项目: ValidateCookie()
        """
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")
        try:
            resp = self.session.post(
                f"{API_BASE}/modules/sportVenue/getOpeningRoom.do",
                data={
                    "XMDM": "001",
                    "YYRQ": today,
                    "YYLX": "1.0",
                    "KSSJ": "11:00",
                    "JSSJ": "12:00",
                    "XQDM": "1",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if "datas" in data:
                    logger.info("✅ Session 有效")
                    return True
            logger.warning(f"Session 无效: {resp.status_code} {resp.text[:200]}")
            return False
        except Exception as e:
            logger.warning(f"验证失败: {e}")
            return False

    # ─── 调试工具 ───────────────────────────────────────

    def debug_query_raw(self, date: str, begin_hour: str = "18", end_hour: str = "19") -> dict:
        """调试用：返回查询接口的原始 JSON"""
        resp = self.session.post(
            f"{API_BASE}/modules/sportVenue/getOpeningRoom.do",
            data={
                "XMDM": "001",
                "YYRQ": date,
                "YYLX": "1.0",
                "KSSJ": f"{begin_hour}:00",
                "JSSJ": f"{end_hour}:00",
                "XQDM": "1",
            },
            timeout=10,
        )
        data = resp.json()
        logger.info(f"顶层 keys: {list(data.keys())}")
        try:
            rows = data["datas"]["getOpeningRoom"]["rows"]
            if rows:
                logger.info(f"第一条 keys: {list(rows[0].keys())}")
                logger.info(f"第一条数据: {rows[0]}")
                logger.info(f"共 {len(rows)} 条，可用 {sum(1 for r in rows if not r.get('disabled', True))} 条")
        except (KeyError, TypeError, IndexError) as e:
            logger.warning(f"解析失败: {e}")
            logger.info(f"原始数据: {str(data)[:500]}")
        return data
