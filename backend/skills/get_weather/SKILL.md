---
name: get_weather
description: 获取指定城市的实时天气信息
---

# 技能：获取实时天气 (get_weather)

本技能教你如何查询任意城市的实时天气。你**没有** `get_weather()` 函数，
而是按下面的步骤，使用你内置的 Core Tools 来完成。

## 推荐方式：使用 wttr.in（无需 API Key）

`wttr.in` 是一个免费的天气服务，支持直接通过 URL 获取纯文本天气。

**步骤：**

1. 用 `fetch_url` 工具访问以下 URL（把 `{city}` 替换为目标城市的英文或拼音名）：

   ```
   https://wttr.in/{city}?format=j1
   ```

   例如查询北京：`https://wttr.in/Beijing?format=j1`
   （`format=j1` 返回 JSON；若想要简洁文本，可用 `https://wttr.in/Beijing?format=3`）

2. 如果返回的是 JSON，使用 `python_repl` 解析关键字段：
   - `current_condition[0].temp_C`：当前温度（摄氏）
   - `current_condition[0].weatherDesc[0].value`：天气描述
   - `current_condition[0].humidity`：湿度
   - `current_condition[0].windspeedKmph`：风速

   示例代码：

   ```python
   import json
   data = json.loads(raw_text)  # raw_text 为 fetch_url 返回的内容
   cur = data["current_condition"][0]
   print(f"温度: {cur['temp_C']}°C, 天气: {cur['weatherDesc'][0]['value']}, 湿度: {cur['humidity']}%")
   ```

3. 用自然语言把结果总结给用户。

## 备选方式：简洁文本

如果只需要一句话概览，直接 `fetch_url` 访问：

```
https://wttr.in/Beijing?format=%l:+%c+%t+%h+%w
```

它会返回类似 `Beijing: ☀️ +5°C 40% ↗12km/h` 的单行结果，可直接转述给用户。

## 注意

- 中文城市名建议转成英文/拼音（如"北京"→"Beijing"）以提高识别率。
- 若 `fetch_url` 返回为空或报错，尝试备选方式或换一种 format 参数重试一次。
