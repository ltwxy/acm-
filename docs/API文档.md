# 刷题管理系统 API 文档

> 本文档记录所有 Flask API 端点，供前端和其他集成使用。

---

## 基础信息

- **Base URL**: `http://localhost:5000`
- **响应格式**: JSON
- **认证**: 无需认证（本地使用）

---

## Web 页面路由

### `GET /`

主页 - 统计面板

**响应**: HTML 页面（index.html）

---

### `GET /plan`

每日训练计划页面

**响应**: HTML 页面（plan.html）

---

### `GET /guide`

命名规范手册

**响应**: HTML 页面（guide.html）

---

### `GET /settings`

设置页面

**响应**: HTML 页面（settings.html）

---

## 统计类 API

### `GET /api/stats`

获取统计数据

**响应示例**:
```json
{
  "success": true,
  "total_problems": 84,
  "platform_stats": {
    "luogu": {"count": 50, "percentage": 62.5},
    "codeforces": {"count": 20, "percentage": 25.0}
  },
  "category_stats": {
    "动态规划": 25,
    "贪心": 15,
    "图论": 12
  },
  "difficulty_stats": {
    "1": 5, "2": 8, "3": 20, "4": 25, "5": 15, "6": 8, "7": 3
  },
  "by_tags": {"dp": 25, "greedy": 15}
}
```

---

### `GET /api/problems`

获取题目列表

**查询参数**:
- `category` (string, optional): 分类筛选
- `platform` (string, optional): 平台筛选
- `status` (string, optional): 状态筛选
- `search` (string, optional): 搜索关键词

**响应**:
```json
{
  "success": true,
  "problems": [
    {
      "id": 1,
      "title": "P1001 A+B Problem",
      "platform": "luogu",
      "problem_id": "P1001",
      "difficulty": 1,
      "category": "基础",
      "status": "solved",
      "url": "https://www.luogu.com.cn/problem/P1001"
    }
  ],
  "total": 84
}
```

---

### `GET /api/platform-problems`

获取平台题目列表

**查询参数**:
- `platform` (string, optional): 平台筛选
- `category` (string, optional): 分类筛选

**响应**:
```json
{
  "success": true,
  "problems": [
    {
      "id": 1,
      "platform": "codeforces",
      "problem_id": "1822A",
      "title": "Unit Array",
      "difficulty": 4,
      "tags": ["math", "greedy"],
      "url": "https://codeforces.com/contest/1822/problem/A"
    }
  ]
}
```

---

### `GET /api/user-stats`

获取用户统计

**响应**:
```json
{
  "success": true,
  "streak_days": 5,
  "training_mode": "distributed",
  "weakness_analysis": "您的动态规划掌握度较低，建议加强..."
}
```

---

## 配置类 API

### `GET /api/config`

获取当前配置

**响应**:
```json
{
  "target_folder": "E:/大学/大学/编程/Save-point/日常刷题",
  "competition_mode": "acm",
  "training_mode": "distributed",
  "deepseek_api_key": "sk-xxx",
  "platform_accounts": {
    "luogu": "username",
    "codeforces": "handle"
  }
}
```

---

### `POST /api/config`

保存配置

**请求体**:
```json
{
  "target_folder": "E:/新的刷题路径",
  "competition_mode": "acm",
  "training_mode": "distributed",
  "deepseek_api_key": "sk-newkey",
  "platform_accounts": {
    "luogu": "new_username"
  },
  "user_goals": "准备NOIP提高组",
  "current_level": "3",
  "candidate_reset_hour": 8,
  "candidate_count": 20
}
```

**响应**:
```json
{"success": true}
```

---

## AI 类 API

### `POST /api/chat`

AI 对话（支持上下文）

**请求体**:
```json
{
  "message": "我想练习动态规划，有什么推荐吗？",
  "history": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！"}
  ]
}
```

**响应**:
```json
{
  "success": true,
  "response": "根据您的刷题数据，我推荐以下题目...",
  "recommendations": [
    {
      "platform": "codeforces",
      "problem_id": "1822D",
      "title": "DP练习题",
      "difficulty": 5,
      "reason": "适合巩固基础DP"
    }
  ]
}
```

**超时**: 60 秒

---

### `POST /api/advice`

获取 AI 学习建议

**请求体**:
```json
{
  "force_refresh": false
}
```

**响应**:
```json
{
  "success": true,
  "advice": "根据您的刷题数据...",
  "cached": true,
  "cache_time": "2026-04-01T12:00:00"
}
```

---

## 每日计划 API

### `GET /api/plan`

获取今日训练计划

**响应**:
```json
{
  "success": true,
  "plan": {
    "date": "2026-04-01",
    "training_mode": "distributed",
    "tasks": [
      {
        "id": 1,
        "problem_id": "P1001",
        "title": "A+B Problem",
        "platform": "luogu",
        "difficulty": 1,
        "priority": "high",
        "reason": "温故知新",
        "status": "pending"
      }
    ]
  }
}
```

---

### `POST /api/plan/generate`

生成每日训练计划

**请求体**:
```json
{
  "force": false
}
```

**响应**:
```json
{
  "success": true,
  "plan": {
    "date": "2026-04-01",
    "tasks_count": 5
  },
  "message": "已生成5道训练题目"
}
```

---

### `POST /api/task/add`

添加任务到今日计划

**请求体**:
```json
{
  "platform": "luogu",
  "problem_id": "P1047",
  "title": "校门外的树",
  "difficulty": 2,
  "tags": ["greedy"],
  "reason": "练习贪心算法",
  "priority": "normal",
  "source": "manual"
}
```

**响应**:
```json
{
  "success": true,
  "task_id": 10
}
```

---

### `POST /api/task/complete`

标记任务完成

**请求体**:
```json
{
  "task_id": 1,
  "feedback": "一次AC，很顺利"
}
```

**响应**:
```json
{
  "success": true
}
```

---

### `POST /api/task/skip`

跳过任务

**请求体**:
```json
{
  "task_id": 2,
  "reason": "太难了"
}
```

**响应**:
```json
{
  "success": true
}
```

---

## 平台同步 API

### `POST /api/platform/sync`

同步平台数据

**请求体**:
```json
{
  "platform": "all",
  "force": false
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| platform | string | 平台名，`all` 表示全部 |
| force | bool | true=全量同步，false=增量同步 |

**响应**:
```json
{
  "success": true,
  "summary": "成功同步3个平台",
  "results": [
    {
      "platform": "luogu",
      "success": true,
      "sync_type": "incremental",
      "fetched": 10,
      "added": 3,
      "skipped": 7
    }
  ]
}
```

---

### `GET /api/platform/sync-status`

获取同步状态

**响应**:
```json
{
  "success": true,
  "platforms": [
    {
      "name": "luogu",
      "problem_count": 50,
      "last_sync": "2026-04-01T12:00:00"
    }
  ],
  "sync_history": [
    {
      "platform": "luogu",
      "sync_type": "incremental",
      "problems_fetched": 10,
      "status": "success",
      "started_at": "2026-04-01T12:00:00"
    }
  ]
}
```

---

## 备份恢复 API

### `POST /api/backup/create`

创建数据库备份

**响应**:
```json
{
  "success": true,
  "name": "backup_20260401_120000",
  "created_at": "2026-04-01T12:00:00",
  "db_size": 294912,
  "tables": {
    "problems": 84,
    "platform_problems": 64,
    "candidate_pool": 15
  },
  "zip_path": "backups/backup_20260401_120000.zip"
}
```

---

### `GET /api/backup/list`

列出所有备份

**响应**:
```json
{
  "success": true,
  "backups": [
    {
      "name": "backup_20260401_120000",
      "created_at": "2026-04-01T12:00:00",
      "db_size": 294912,
      "tables": {"problems": 84}
    }
  ]
}
```

---

### `POST /api/backup/restore`

恢复备份

**请求体**:
```json
{
  "name": "backup_20260401_120000"
}
```

**响应**:
```json
{
  "success": true,
  "message": "已成功恢复到备份 'backup_20260401_120000'",
  "pre_restore_backup": "pre_restore_20260401_130000.db"
}
```

> ⚠️ 恢复前会自动备份当前数据

---

### `POST /api/backup/delete`

删除备份

**请求体**:
```json
{
  "name": "backup_20260401_120000"
}
```

**响应**:
```json
{
  "success": true,
  "deleted": ["backups/backup_20260401_120000.db"]
}
```

---

## 候选题目池 API

### `GET /api/candidates`

获取候选题目池

**响应**:
```json
{
  "success": true,
  "candidates": [
    {
      "id": 1,
      "platform": "codeforces",
      "problem_id": "1822D",
      "title": "DP练习题",
      "difficulty": 5,
      "difficulty_normalized": 6,
      "tags": ["dp", "implementation"],
      "category": "动态规划",
      "url": "https://codeforces.com/contest/1822/problem/D",
      "reason": "适合当前水平",
      "priority": 1,
      "status": "pending"
    }
  ]
}
```

---

### `POST /api/candidate/generate`

生成新的候选题目

**响应**:
```json
{
  "success": true,
  "count": 15,
  "message": "已生成15道推荐题目"
}
```

**超时**: 90 秒

---

### `POST /api/candidate/mark`

标记候选题目状态

**请求体**:
```json
{
  "id": 1,
  "action": "done"
}
```

| action | 说明 |
|--------|------|
| `done` | 已刷过 |
| `skip` | 太难跳过 |
| `cancel` | 取消 |

**响应**:
```json
{
  "success": true,
  "message": "已标记为'已刷过'"
}
```

---

## 报告 API

### `POST /api/report`

生成分析报告

**请求体**:
```json
{
  "format": "html"
}
```

**响应**: HTML 格式报告或 JSON

---

## 错误响应

所有 API 在出错时返回：

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

常见 HTTP 状态码：
- `200` - 成功
- `400` - 请求参数错误
- `500` - 服务器内部错误
