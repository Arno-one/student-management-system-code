from fastapi import FastAPI
from database import Session
from model import Teacher
from model.Class import Class
from DAO.teacher_information_CRUD import teacher_table_CRUD
from API.teacher_information_API_Router import teacher_information_router
from datetime import datetime
import uvicorn
import threading

# 建表 + 插入班级数据
db = Session()
dao = teacher_table_CRUD(db)
Teacher.Base.metadata.drop_all(Teacher.engine)
Teacher.Base.metadata.create_all(Teacher.engine)

now = datetime.now()
db.add_all([
    Class(class_code="C001", class_name="三年级1班", start_time=now, head_teacher_id=1),
    Class(class_code="C002", class_name="三年级2班", start_time=now, head_teacher_id=2),
    Class(class_code="C003", class_name="四年级1班", start_time=now, head_teacher_id=3),
])
db.commit()
db.close()

# 启动服务器
app = FastAPI()
app.include_router(teacher_information_router)

server = threading.Thread(
    target=uvicorn.run,
    kwargs={"app": app, "host": "127.0.0.1", "port": 8765, "log_level": "error"},
    daemon=True,
)
server.start()

import time, urllib.request, json, urllib.parse

def request(method, path, body=None, params=None):
    url = f"http://127.0.0.1:8765{path}"
    if params:
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{query}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8") if e.fp else str(e)
        return e.code, msg

time.sleep(2)

print("=" * 50)
print("1. GET /teachers（空表，应返回空 items）")
code, resp = request("GET", "/teachers")
assert code == 200 and resp["items"] == [] and resp["total"] == 0, f"FAIL: {code} {resp}"
print("PASS: 空表返回 items=[], total=0")

print("\n" + "=" * 50)
print("2. POST /teachers（新增 3 条记录）")
new_teachers = [
    {"name": "张三", "gender": "男", "phone": "13800138001", "email": "zhangsan@qq.com",
     "title": "班主任", "class_id": 1, "hire_date": "2024-09-01T00:00:00"},
    {"name": "李四", "gender": "女", "phone": "13800138002", "email": "lisi@qq.com",
     "title": "数学老师", "class_id": 2, "hire_date": "2024-09-01T00:00:00"},
    {"name": "王五", "gender": "男", "phone": "13800138003",
     "title": "英语老师", "class_id": 3, "hire_date": "2024-09-01T00:00:00",
     "birth_date": "1990-05-15T00:00:00"},
]
code, resp = request("POST", "/teachers", new_teachers)
print(f"状态码: {code}, 响应: {resp}")

print("\n" + "=" * 50)
print("3. GET /teachers（应返回 3 条，gender 为中文，含分页元数据）")
code, resp = request("GET", "/teachers")
assert code == 200, f"FAIL: {code}"
items = resp["items"]
assert resp["total"] == 3, f"FAIL: total 应为 3，实际 {resp['total']}"
assert resp["page"] == 1 and resp["page_size"] == 20
assert resp["total_pages"] == 1
assert len(items) == 3, f"FAIL: 应为 3 条，实际 {len(items)}"
assert items[0]["gender"] in ("男", "女"), f"FAIL: gender 应为中文"
print(f"PASS: total={resp['total']}, page={resp['page']}/{resp['total_pages']}")
print(json.dumps(items, ensure_ascii=False, indent=2))

print("\n" + "=" * 50)
print("4. GET /teachers/2（单条查询）")
code, resp = request("GET", "/teachers/2")
assert code == 200, f"FAIL: {code}"
assert resp["name"] == "李四" and resp["gender"] == "女", f"FAIL: {resp}"
print("PASS:", json.dumps(resp, ensure_ascii=False, indent=2))

print("\n" + "=" * 50)
print("5. GET /teachers/999（不存在，验证报错）")
code, resp = request("GET", "/teachers/999")
print(f"状态码: {code}（非 200 即为检测到异常）")

print("\n" + "=" * 50)
print("6. PUT /teachers/1（全字段更新）")
update = {"name": "张三丰", "gender": "男", "phone": "13900139001",
          "title": "年级主任", "class_id": 10, "hire_date": "2025-01-01T00:00:00"}
code, resp = request("PUT", "/teachers/1", update)
print(f"状态码: {code}, 响应: {resp}")
code, resp = request("GET", "/teachers/1")
print(f"更新后: {json.dumps(resp, ensure_ascii=False, indent=2)}")

print("\n" + "=" * 50)
print("7. PUT /teachers/2（部分字段更新，只改 phone）")
code, resp = request("PUT", "/teachers/2", {"phone": "13700137001"})
print(f"状态码: {code}, 响应: {resp}")
code, resp = request("GET", "/teachers/2")
print(f"更新后: {json.dumps(resp, ensure_ascii=False, indent=2)}")

print("\n" + "=" * 50)
print("8. GET /teachers?name=张（模糊查询姓名）")
code, resp = request("GET", "/teachers", params={"name": "张"})
items = resp["items"]
assert code == 200 and resp["total"] >= 1, f"FAIL: {code} {resp}"
assert any("张" in t["name"] for t in items), f"FAIL: name 不包含 '张'"
print(f"PASS: {resp['total']} 条匹配")

print("\n" + "=" * 50)
print("9. GET /teachers?gender=男（按性别筛选）")
code, resp = request("GET", "/teachers", params={"gender": "男"})
items = resp["items"]
assert code == 200 and resp["total"] == 2, f"FAIL: 应为 2 男，实际 {resp['total']}"
assert all(t["gender"] == "男" for t in items), f"FAIL: 存在非男性记录"
print("PASS: 2 条男性记录")

print("\n" + "=" * 50)
print("10. GET /teachers?title=数学老师（按职称筛选）")
code, resp = request("GET", "/teachers", params={"title": "数学老师"})
items = resp["items"]
assert code == 200 and resp["total"] == 1, f"FAIL: {code} {resp}"
assert items[0]["name"] == "李四", f"FAIL: 期望李四"
print("PASS:", items[0]["name"])

print("\n" + "=" * 50)
print("11. GET /teachers?class_id=2（按班级筛选）")
code, resp = request("GET", "/teachers", params={"class_id": 2})
items = resp["items"]
assert code == 200 and resp["total"] == 1, f"FAIL: {code} {resp}"
assert items[0]["class_name"] == "三年级2班", f"FAIL: {resp}"
print("PASS:", items[0]["name"], items[0]["class_name"])

print("\n" + "=" * 50)
print("12. GET /teachers?hire_date_range（日期范围）")
code, resp = request("GET", "/teachers", params={
    "hire_date_start": "2024-09-01T00:00:00",
    "hire_date_end": "2024-09-01T00:00:00",
})
items = resp["items"]
assert code == 200 and resp["total"] == 2, f"FAIL: {code} {resp}"
print(f"PASS: {resp['total']} 条在 2024-09-01 入职")

print("\n" + "=" * 50)
print("13. GET /teachers?sort_by=hire_date&sort_order=desc（按入职日期降序）")
code, resp = request("GET", "/teachers", params={"sort_by": "hire_date", "sort_order": "desc"})
items = resp["items"]
assert code == 200, f"FAIL: {code}"
assert items[0]["hire_date"] >= items[-1]["hire_date"], f"FAIL: 未按降序排列"
print(f"PASS: {items[0]['name']}({items[0]['hire_date']}) → {items[-1]['name']}({items[-1]['hire_date']})")

print("\n" + "=" * 50)
print("14. GET /teachers?sort_by=id&sort_order=asc（纯排序，无筛选）")
code, resp = request("GET", "/teachers", params={"sort_by": "id", "sort_order": "asc"})
items = resp["items"]
assert code == 200 and resp["total"] == 3, f"FAIL: {code} {resp}"
assert items[0]["id"] < items[-1]["id"], f"FAIL: 未按 id 升序"
print(f"PASS: 3 条, id 升序 {items[0]['id']}→{items[-1]['id']}")

print("\n" + "=" * 50)
print("15. GET /teachers?sort_by=invalid（非法排序字段，422 拒绝）")
code, resp = request("GET", "/teachers", params={"sort_by": "invalid"})
assert code == 422, f"FAIL: {code}，期望 422"
print(f"PASS: 状态码 {code}，正确拒绝非法参数")

# ===== 分页测试 =====
print("\n" + "=" * 50)
print("16. GET /teachers?page=1&page_size=2（分页第 1 页，每页 2 条）")
code, resp = request("GET", "/teachers", params={"page": 1, "page_size": 2})
items = resp["items"]
assert code == 200, f"FAIL: {code}"
assert resp["total"] == 3, f"FAIL: total 应为 3"
assert resp["page"] == 1 and resp["page_size"] == 2
assert resp["total_pages"] == 2
assert len(items) == 2, f"FAIL: 应返回 2 条，实际 {len(items)}"
print(f"PASS: total={resp['total']}, page={resp['page']}/{resp['total_pages']}, items={len(items)}")

print("\n" + "=" * 50)
print("17. GET /teachers?page=2&page_size=2（分页第 2 页，应返回剩余 1 条）")
code, resp = request("GET", "/teachers", params={"page": 2, "page_size": 2})
items = resp["items"]
assert code == 200 and resp["total"] == 3, f"FAIL: {code} {resp}"
assert resp["page"] == 2 and resp["total_pages"] == 2
assert len(items) == 1, f"FAIL: 应返回 1 条，实际 {len(items)}"
print(f"PASS: total={resp['total']}, page={resp['page']}/{resp['total_pages']}, items={len(items)}")

print("\n" + "=" * 50)
print("18. GET /teachers?page=999&page_size=2（超出范围的页码，空列表）")
code, resp = request("GET", "/teachers", params={"page": 999, "page_size": 2})
items = resp["items"]
assert code == 200 and resp["total"] == 3, f"FAIL: {code} {resp}"
assert resp["total_pages"] == 2
assert len(items) == 0, f"FAIL: 应返回空列表"
print(f"PASS: total={resp['total']}, page=999/{resp['total_pages']}, items=[]")

print("\n" + "=" * 50)
print("19. GET /teachers?gender=男&page=1&page_size=1（筛选 + 分页组合）")
code, resp = request("GET", "/teachers", params={"gender": "男", "page": 1, "page_size": 1})
items = resp["items"]
assert code == 200 and resp["total"] == 2, f"FAIL: total 应为 2，{resp}"
assert resp["total_pages"] == 2
assert len(items) == 1 and items[0]["gender"] == "男"
print(f"PASS: 筛选后 total={resp['total']}, 第 1 页 {len(items)} 条")

print("\n" + "=" * 50)
print("20. 全部测试完成")
