"""伊家人酒店 · 联盟会员中枢接入（调用悦聚食材平台）"""
import httpx

ECO_BASE_URL = "https://7yijia888.com/premium/api"
ECO_KEY = "yueju-eco-key-2026"
ECO_PARTNER_ID = 1  # 悦聚大酒店（住宿）在食材平台的联盟商家 id


async def verify_member(code: str):
    """验证联盟会员码 → (ok, name, discount)"""
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(
                ECO_BASE_URL + "/eco/member-verify",
                json={"eco_key": ECO_KEY, "code": (code or "").strip()},
            )
            d = r.json()
    except Exception as e:
        return False, f"会员中枢调用失败：{e}", None
    if d.get("code") == 0:
        data = d.get("data") or {}
        return True, data.get("name", ""), data.get("discount", 0.9)
    return False, d.get("msg", "会员码无效"), None


async def report_consume(code: str, amount: float, remark: str = ""):
    """上报跨系统消费 → (ok, pay_amount, commission)"""
    try:
        async with httpx.AsyncClient(timeout=8) as c:
            r = await c.post(
                ECO_BASE_URL + "/eco/consume-report",
                json={
                    "eco_key": ECO_KEY,
                    "code": (code or "").strip(),
                    "system": "hotel",
                    "partner_id": ECO_PARTNER_ID,
                    "amount": amount,
                    "remark": remark,
                },
            )
            d = r.json()
    except Exception as e:
        return False, f"上报失败：{e}", None
    if d.get("code") == 0:
        data = d.get("data") or {}
        return True, data.get("pay_amount"), data.get("commission")
    return False, d.get("msg", "上报失败"), None
