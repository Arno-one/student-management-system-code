# Agent系统v2.3-周边服务口语餐饮关键词回归测试

## 一、问题背景

用户输入：

```text
宝安中心附近有什么好吃的
```

修复前解析链路能识别为周边服务意图，但服务关键词会停留在口语词“好吃”，工具层继续按“好吃”调用地图 POI 搜索，容易返回空结果。

## 二、修复目标

将“好吃”“好吃的”“吃啥”“吃什么”等常见口语餐饮问法统一归一为地图更稳定的 POI 关键词：

```text
餐饮
```

## 三、回归用例

### 用例 1：宝安中心附近有什么好吃的

输入：

```text
宝安中心附近有什么好吃的
```

预期解析结果：

```text
is_nearby=True
center_text=宝安中心
query_text=好吃
keyword=餐饮
radius_meters=2000
limit=10
missing_fields=[]
```

验证命令：

```text
python -c "from agent_system.middleware.nearby_parser import parse_nearby_request; r=parse_nearby_request('宝安中心附近有什么好吃的'); print(r.keyword.encode('unicode_escape').decode()); print(r.center_text.encode('unicode_escape').decode()); print(r.query_text.encode('unicode_escape').decode())"
```

实际结果：

```text
\u9910\u996e
\u5b9d\u5b89\u4e2d\u5fc3
\u597d\u5403
```

说明：

```text
\u9910\u996e = 餐饮
\u5b9d\u5b89\u4e2d\u5fc3 = 宝安中心
\u597d\u5403 = 好吃
```

结论：通过。

### 用例 2：深圳宝安中心的壹方城购物中心有什么餐饮推荐的

问题背景：

```text
这类问法没有显式出现“附近/周边”，但语义上仍是“指定地点 + 服务类别”的 POI 推荐。
修复前 nearby parser 返回 is_nearby=False，中间件直接放行，后续如果意图分类器命中 nearby_service，工具层会因为缺少地点或服务类型返回 clarification。
```

输入：

```text
深圳宝安中心的壹方城购物中心有什么餐饮推荐的
```

预期解析结果：

```text
is_nearby=True
center_text=深圳宝安中心的壹方城购物中心
query_text=餐饮
keyword=餐饮
radius_meters=2000
limit=10
missing_fields=[]
```

验证命令：

```text
python -X utf8 -c "from agent_system.middleware.nearby_parser import parse_nearby_request; r=parse_nearby_request('深圳宝安中心的壹方城购物中心有什么餐饮推荐的'); assert r.is_nearby and r.center_text=='深圳宝安中心的壹方城购物中心' and r.keyword=='餐饮' and not r.missing_fields; print('nearby mall dining regression passed')"
```

实际结果：

```text
nearby mall dining regression passed
```

结论：通过。

### 用例 3：边界场景不误判

输入：

```text
从宝安到龙岗坐地铁怎么去
学校有什么餐饮推荐
```

预期解析结果：

```text
通勤句：is_nearby=False，继续交给通勤规划链路
模糊学校：is_nearby=True，但 missing_fields=["center"]，提示用户补具体地点
```

结论：通过。

## 四、编译验证

命令：

```text
python -m compileall agent_system DAO model main.py
```

结果：

```text
后端编译通过
```

结论：通过。
