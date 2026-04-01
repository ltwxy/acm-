# 刷题管理系统 (Code Practice Manager)

> 自动化刷题数据管理 + AI 学习建议 + 多平台进度同步，为算法竞赛玩家打造的智能训练助手

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-blue.svg)](https://www.deepseek.com)
![Platforms](https://img.shields.io/badge/Platforms-Luogu%7CCF%7CAtCoder%7CNowCoder-orange)

---

## 功能亮点

- **自动扫描** - 监听指定文件夹，自动识别 .cpp 文件并解析算法类型
- **AI 智能助手** - 基于 DeepSeek API 的对话式学习指导，支持上下文理解
- **多平台同步** - 洛谷、Codeforces、AtCoder、牛客 账号绑定与数据同步
- **可视化面板** - Web 统计面板：知识点分布、难度分布、平台对比图表
- **AI 学习建议** - 分析薄弱环节，生成个性化学习路径和推荐题目
- **综合分析报告** - SWOT 分析、学习轨迹、个性化建议报告
- **每日训练计划** - AI 推荐选题 + 手动添加任务，支持打卡追踪
- **题目难度归一化** - 将洛谷 1-7、CF Rating 等映射为统一 1-10 标准
- **数据备份恢复** - 一键备份/恢复数据库，防止数据丢失
- **系统自检** - 自动检测配置、环境、依赖、连接状态

---

## 快速开始

### 环境要求
- Python 3.8+
- Windows / macOS / Linux

### 安装依赖
```bash
pip install flask watchdog requests
# 或
pip install -r requirements.txt
```

### 配置
编辑 config.json：
```json
{
    "target_folder": "E:/你的刷题文件夹",
    "deepseek_api_key": "sk-xxx",
    "competition_mode": "acm",
    "platform_accounts": {
        "luogu": "你的洛谷用户名",
        "codeforces": "你的CF Handle",
        "atcoder": "你的AtCoder用户名",
        "nowcoder": "你的牛客用户名"
    }
}
```

### 启动方式

**方式一：Web 面板模式（推荐）**
```bash
python main.py init    # 首次运行，初始化数据库
python main.py web     # 启动 Web 面板
```
然后访问 http://localhost:5000

**方式二：命令行模式**
```bash
python main.py scan    # 扫描本地刷题文件
python main.py watch   # 启动文件监控（自动扫描新增文件）
python main.py report  # 生成学习报告
```

### 首次配置

1. 复制配置文件：
   ```bash
   cp config.example.json config.json
   ```

2. 编辑 `config.json`，填入你的配置：
   ```json
   {
       "target_folder": "E:/你的刷题文件夹",
       "deepseek_api_key": "sk-你的API密钥",
       "platform_accounts": {
           "luogu": "你的洛谷用户名",
           "codeforces": "你的CF Handle"
       }
   }
   ```

3. 获取 DeepSeek API Key：访问 https://platform.deepseek.com 注册获取

---

## 文件命名规范

| 平台 | 命名示例 | 说明 |
|------|----------|------|
| 洛谷 入门 | B3626_跳跃机器人.cpp | B + 题号 |
| 洛谷 题库 | P1314_聪明的质检员.cpp | P + 题号 |
| 洛谷 模板/练习 | T/UBxxx.cpp | T/U + 题号 |
| Codeforces | CF1822A_题目名.cpp | CF + Round + 字母 |
| AtCoder | AT_abc301_a.cpp | AT_ + abc/contest |
| 牛客 | NC12345_题目名.cpp | NC + 题号 |
| USACO | USACO_bronze_xxx.cpp | USACO_难度_名称 |

> 更多规范请访问：http://localhost:5000/guide

---

## 核心功能详解

### 1. Web 统计面板 (/)

- 数据概览：总题数、解决率、平台分布
- 图表分析：知识点分布图（50+分类翻译）、难度分布图
- 题目列表：按分类/平台/状态筛选，点击跳转题目
- AI 对话助手：基于上下文的智能题目推荐
- 候选题目池：AI 推荐待练习题目，支持标记"已刷过"/"太难"

### 2. 每日训练计划 (/plan)

- AI 推荐选题：结合用户目标、当前水平、训练模式综合推荐
- 手动添加任务：支持按平台、题号、标签快速添加
- 任务执行追踪：标记完成状态，记录用时反馈
- 灵活的训练模式：ACM 模式（一次 AC）/ OI 模式（看结果评分）

### 3. 平台数据同步

| 平台 | 数据同步 | 难度归一化 |
|------|----------|------------|
| 洛谷 | 题目列表 | 1-7 -> 1-10 |
| Codeforces | Rating/题目 | Rating -> 1-10 |
| AtCoder | Rating/题目 | ABC/ARC/AGC -> 1-10 |
| 牛客 | 题目列表 | 简单/中等/困难 -> 1-10 |

- 增量同步：自动跳过已保存题目，只获取新增记录
- 全量同步：重新获取所有数据（数据异常时使用）

### 4. AI 学习建议

基于 DeepSeek API 分析：
- 刷题数据统计（知识点分布、难度趋势）
- 薄弱环节识别（知识点掌握度 < 60% 标记为薄弱）
- 个性化学习路径（结合竞赛模式、目标方向）
- 推荐下一步训练方向

### 5. 系统自检

```bash
python scripts/system_check.py
```
检查项目：Python 版本和依赖包 / 配置文件完整性 / 数据库表结构和索引 / 文件夹结构 / Web 服务状态 / 网络连接状态

---

## 项目结构

```
刷题管理系统/
├── main.py                 # 主入口（CLI 命令行）
├── config.py               # 配置定义（分类、算法模式）
├── config.json             # 用户配置（API Key、账号、路径）
├── requirements.txt        # Python 依赖
│
├── core/
│   ├── database.py         # SQLite 数据库管理（9张表）
│   ├── analyzer.py          # 代码分析（算法识别、文件解析）
│   ├── file_manager.py      # 文件监控（watchdog）
│   ├── platform_fetcher.py  # 多平台数据爬取
│   ├── ai_chat.py           # AI 对话（DeepSeek）
│   ├── ai_advisor.py        # AI 学习建议
│   ├── daily_plan_generator.py  # 每日计划生成
│   ├── mastery_calculator.py    # 掌握度计算
│   ├── weakness_analyzer.py     # 弱点分析
│   ├── report_generator.py       # 报告生成
│   └── backup_manager.py    # 数据备份与恢复
│
├── web/
│   ├── app.py              # Flask 应用（40+ API 端点）
│   └── templates/
│       ├── index.html       # 主页（统计面板 + AI 对话）
│       ├── plan.html        # 训练计划页面
│       ├── settings.html    # 设置页面
│       └── guide.html       # 命名规范手册
│
├── scripts/
│   ├── crawl_platform_problems.py  # 平台题目爬取
│   ├── optimize_indexes.py          # 数据库索引优化
│   └── system_check.py              # 系统自检脚本
│
├── data/
│   ├── problems.db          # SQLite 数据库
│   └── ai_advice_cache.json  # AI 建议缓存
│
└── docs/
    └── 系统设计.md           # 系统设计文档
```

### 数据库表结构

| 表名 | 说明 |
|------|------|
| problems | 本地代码文件题目 |
| platform_problems | 平台已解题 |
| candidate_pool | AI 候选题目池 |
| task_execution | 训练计划任务 |
| daily_plans | 每日计划 |
| sync_log | 同步记录 |
| problem_status_log | 题目状态变更记录 |

---

## 配置项说明

| 配置项 | 类型 | 说明 |
|--------|------|------|
| target_folder | string | 刷题文件夹路径 |
| deepseek_api_key | string | DeepSeek API 密钥 |
| competition_mode | string | acm 或 oi |
| training_mode | string | distributed（分散练习）或 focused（专项突破） |
| user_goals | string | 训练目标（自由文本） |
| current_level | string | 当前水平（1-5档） |
| platform_accounts | object | 各平台用户名 |
| candidate_reset_hour | int | 候选池自动刷新时间（小时，0-23） |
| candidate_count | int | 每次推荐的候选题目数量 |

---

## 难度归一化对照表

| 标准难度 | 洛谷 | Codeforces | 牛客 |
|---------|------|-------------|------|
| 1 | 入门 | 800 | 简单 |
| 2 | 普及- | 900 | - |
| 3 | 普及/ | 1000 | - |
| 4 | 普及+ | 1200 | - |
| 5 | 提高 | 1400 | 中等 |
| 6 | 提高+ | 1600/1800 | - |
| 7 | 省选 | 2000/2200 | 困难 |
| 8 | NOI | 2400/2500 | - |
| 9 | NOI+ | 2600+ | - |
| 10 | - | 2800+ | - |

---

## 安装部署

### 快速安装

```bash
# 克隆项目
git clone https://github.com/ltwxy/acm-.git
cd acm-

# 安装依赖
pip install -r requirements.txt

# 配置
cp config.example.json config.json
# 编辑 config.json 填入你的信息

# 启动
python main.py init
python main.py web
```

### 目录结构要求

确保你的刷题文件夹中的 `.cpp` 文件遵循命名规范：

| 平台 | 命名示例 |
|------|----------|
| 洛谷 | `P1001_A+BProblem.cpp`, `B3626_跳跃机器人.cpp` |
| Codeforces | `CF1822A.cpp`, `CF1690C_ShoeShuffling.cpp` |
| AtCoder | `AT_abc301_a.cpp` |
| 牛客 | `NC12345.cpp` |
| USACO | `USACO_bronze_xxx.cpp` |

---

## 常见问题

**Q: 启动后数据库为空？**
```bash
python main.py scan    # 扫描本地文件
python main.py init   # 初始化数据库
```

**Q: AI 功能无法使用？**
检查 config.json 中的 deepseek_api_key 是否正确配置。

**Q: 平台同步失败？**
确认网络可以访问对应平台，且用户名拼写正确。

**Q: 如何备份数据？**
在 Web 设置页面点击"创建备份"，或运行系统自检脚本查看数据库状态。

---

## 贡献与反馈

欢迎提交 Issue 和 Pull Request！

## License

MIT License

## 致谢

- 洛谷 (https://www.luogu.com.cn) - 优质在线题库
- Codeforces (https://codeforces.com) - 全球竞赛平台
- AtCoder (https://atcoder.jp) - 日本竞赛平台
- DeepSeek (https://www.deepseek.com) - AI 大模型 API
