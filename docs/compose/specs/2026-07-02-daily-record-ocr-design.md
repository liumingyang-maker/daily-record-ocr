# 每日生产记录智能识别系统 - 设计规格书

## [S1] 项目概述

本地化单机软件，用于识别手写《每日生产记录》表格图片，融合 PP-OCR 本地识别、MiMo API 视觉大模型复核、历史电子记录数据库比对，生成结构化生产记录并导出 Excel。

**核心目标：**
- OCR 可以不完美，但不能悄悄错
- 不确定字段必须进入人工确认
- 每个字段可追溯（原图小格子、PP-OCR、MiMo、历史推荐、最终值、人工修改日志）
- 系统越用越准（人工修正和历史导入持续回流知识库）

## [S2] 运行环境

- 操作系统：Windows 单机
- 使用人数：1人
- 每日图片量：最多约 100 张
- 硬件：CPU 可跑通，第一版不依赖 GPU
- 数据库：SQLite
- 导出：Excel xlsx
- 部署：Windows 安装包（one-folder + 启动器 exe）

## [S3] 技术栈

- Python 3.11
- FastAPI + Jinja2 + HTMX/原生 JS
- SQLite + SQLAlchemy + Alembic
- OpenCV（图像处理）
- PaddleOCR / PP-OCRv6 medium（本地 OCR）
- MiMo API（视觉大模型复核）
- openpyxl（Excel 导出）
- YAML + .env（配置）
- pytest（测试）
- NSIS / Inno Setup（安装包）

## [S4] 系统架构（分层）

```
Interface 层: Web 页面、API 路由
Application 层: 业务流程编排
Domain 层: 核心业务模型
Infrastructure 层: OpenCV、PaddleOCR、MiMo API、SQLite、Excel
Config 层: 模板坐标、字段规则、OCR/MiMo 参数
```

## [S5] 核心识别流程

```
图片上传 → 图像校正 → 模板切格(3条记录) → 切分字段小格子
→ PP-OCR 单格识别 → MiMo API 整条记录复核
→ 字段标准化 → 历史数据库比对 → 生成候选结果
→ 规则校验 → 人工确认 → 写入正式记录
→ 更新知识库 → 导出 Excel
```

## [S6] 数据库表清单（20张表）

| 表名 | 用途 |
|------|------|
| recognition_jobs | 识别任务 |
| production_records | 生产记录 |
| record_material_items | 配方明细 |
| record_machine_params | 机器参数 |
| record_temperatures | 温度数据 |
| field_recognition_results | 字段级识别结果（核心） |
| field_candidates | 字段候选值 |
| customers | 客户库 |
| products | 产品/排号库 |
| materials | 物料库 |
| material_aliases | 物料别名 |
| formulas | 历史配方主表 |
| formula_items | 配方明细 |
| manual_correction_logs | 人工修正日志 |
| import_batches | 导入批次 |
| import_staging_records | 导入暂存记录 |
| import_staging_material_items | 导入暂存物料 |
| import_staging_warnings | 导入警告 |
| mimo_request_logs | MiMo 请求日志 |
| mimo_cache | MiMo 缓存 |

## [S7] MiMo 接入策略

- 第一版：`record_level` 模式，每条记录裁剪图调用一次 MiMo
- 支持三种模式：OFF / LOW_CONFIDENCE_ONLY / RECORD_LEVEL
- API Key 从 .env 读取
- 支持 timeout、retry、cache、JSON schema 校验
- 失败不中断任务，进入人工确认
- 一天最多约 300 次调用，成本可控

## [S8] 候选融合算法

每个字段综合多个来源生成候选：
- PP-OCR 单格识别（权重 ~0.25）
- MiMo 记录级识别（权重 ~0.25）
- 物料/客户字典匹配（权重 ~0.20）
- 历史配方相似度（权重 ~0.20）
- 规则合法性（权重 ~0.10）

置信度分级：
- >= 0.95 绿色（可自动标记）
- 0.80-0.95 黄色（需快速确认）
- < 0.80 红色（必须人工处理）

第一版：所有记录进入人工确认页面，由用户一键确认。

## [S9] 历史电子记录导入

支持两种格式：
- 类型A：扁平表格（一行一条记录）
- 类型B：固定模板（类似纸质版排版）

导入流程：上传 → 解析 → staging 暂存 → 预览 → 校验 → 确认 → 写入正式库

从历史记录自动提取：客户库、产品库、物料库、配方库、物料别名库

## [S10] 单位解析

- 保存 5 个值：usage_raw, usage_value, unit_raw, unit_standard, base_quantity_kg
- 可换算单位统一到 kg（g/kg/t）
- 不可换算单位保留原值（包/袋/桶/份）
- 不确定单位标记为历史推荐，不伪装成 OCR 结果

## [S11] Excel 导出（4个Sheet）

1. 生产记录汇总（一条记录一行）
2. 配方明细（一个物料一行）
3. 识别审查（追溯用）
4. 导入/修正摘要

## [S12] 开发阶段规划

| 阶段 | 交付内容 |
|------|----------|
| 1 | 项目骨架 + FastAPI + SQLite + Web + 图片上传 + 任务列表 |
| 2 | 历史电子记录导入（xlsx/csv → staging → 知识库） |
| 3 | 图像校正 + 模板切格（OpenCV） |
| 4 | PP-OCR 单格识别 |
| 5 | MiMo API 接入 |
| 6 | 候选融合 + 历史匹配 |
| 7 | 人工确认页面 |
| 8 | Excel 导出 |
| 9 | Windows 安装包 |

## [S13] 架构约束

1. 不允许所有逻辑写在一个脚本里
2. OCR 引擎抽象成接口，可替换
3. MiMo 独立模块，可关闭
4. 模板坐标使用 YAML 配置，不硬编码
5. 历史导入使用 staging 暂存区
6. 每个字段保存多来源结果
7. 新客户/新物料不强行匹配旧数据
8. 保留人工修正日志
9. 必须有基础单元测试

## [S14] 测试策略

单元测试文件：
- test_unit_parser.py（单位解析）
- test_normalizers.py（标准化）
- test_material_matcher.py（物料匹配）
- test_formula_fingerprint.py（配方指纹）
- test_formula_similarity.py（配方相似度）
- test_import_parser.py（导入解析）
- test_validators.py（规则校验）
- test_excel_exporter.py（Excel 导出）
- test_pipeline.py（完整流程）

## [S15] 策略确认

- 开发策略：按阶段 1-9 逐步实现
- 测试数据：先用 mock 数据开发，后续接入真实数据
- 当前环境：Python 3.14（开发机），目标 Python 3.11（Windows 部署）
