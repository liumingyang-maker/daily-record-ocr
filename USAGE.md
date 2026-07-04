# 每日生产记录智能识别系统 — 使用说明书

## 目录

1. [系统简介](#1-系统简介)
2. [安装部署](#2-安装部署)
3. [功能操作指南](#3-功能操作指南)
4. [配置说明](#4-配置说明)
5. [常见问题](#5-常见问题)

---

## 1. 系统简介

本系统用于识别手写《每日生产记录》表格图片，自动提取生产数据（客户、产品、物料配方、机器参数、温度等），经人工确认后导出 Excel。

### 核心特性

- **智能识别**：OCR + 视觉大模型双重识别，融合历史知识库
- **历史导入**：支持导入历史电子记录，建立知识库，系统越用越准
- **人工确认**：所有不确定字段自动标红，支持手动修正
- **一键导出**：生成标准 Excel 文件，含 4 个 Sheet

### 适用场景

- 每日生产记录的手写表格图片识别
- 历史电子生产记录的知识库建设
- 生产数据的结构化管理和导出

---

## 2. 安装部署

### 2.1 环境要求

- **操作系统**：Windows 10+ / macOS 10.15+ / Linux
- **Python**：3.11 或更高版本
- **内存**：建议 4GB 以上
- **磁盘**：至少 500MB 可用空间

### 2.2 安装步骤

#### 方式一：使用启动脚本（推荐）

**macOS / Linux：**
```bash
# 下载项目后进入目录
cd daily-record-ocr

# 运行启动脚本（自动创建环境、安装依赖、启动服务）
./launcher/run.sh
```

**Windows：**
```cmd
# 下载项目后进入目录
cd daily-record-ocr

# 运行启动脚本
launcher\run.bat
```

首次运行会自动：
1. 创建 Python 虚拟环境
2. 安装所有依赖
3. 启动服务并打开浏览器

#### 方式二：手动安装

```bash
# 1. 克隆项目
git clone https://github.com/liumingyang-maker/daily-record-ocr.git
cd daily-record-ocr

# 2. 创建虚拟环境
python3 -m venv .venv

# 3. 激活虚拟环境
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动服务
python3 -m app.main            # macOS/Linux
# python -m app.main           # Windows
```

### 2.3 访问系统

启动成功后，浏览器访问：**http://127.0.0.1:8765**

---

## 3. 功能操作指南

### 3.1 首页

首页展示系统三大功能入口：
- **识别任务**：上传手写生产记录图片
- **历史导入**：导入历史电子记录
- **物料库**：管理物料信息

### 3.2 上传图片识别

#### 步骤 1：上传图片

1. 点击导航栏「识别任务」
2. 点击「选择文件」按钮，选择手写生产记录图片
3. 支持格式：JPG、PNG、BMP、TIFF
4. 点击「上传图片」

#### 步骤 2：图像预处理

上传后系统自动进行：
- 图片方向校正（横版自动旋转为竖版）
- 对比度增强
- 缩放到标准尺寸（1800×2500）
- 按模板切割 3 条记录区域
- 进一步切割各字段小格子

#### 步骤 3：OCR 识别

系统对每个字段小格子进行文字识别：
- **OCR 引擎**：识别单个字段文字
- **MiMo 大模型**：对整条记录进行复核识别
- **历史匹配**：与知识库中的历史配方比对

#### 步骤 4：候选融合

系统综合多个来源生成候选结果：
- 按置信度排序
- 颜色标记：绿色（≥95%）、黄色（80-95%）、红色（<80%）

#### 步骤 5：人工确认

1. 点击任务列表中的「查看」
2. 点击「识别确认」进入确认页面
3. 检查每个字段的识别结果
4. 点击候选值可快速替换
5. 可直接编辑文本框修改值
6. 点击「全部确认」完成确认

#### 步骤 6：导出 Excel

确认后点击「导出」按钮，生成 Excel 文件，包含：
- **生产记录汇总**：每条记录一行
- **配方明细**：每个物料一行
- **识别审查**：每个字段的识别来源和置信度
- **导入修正摘要**：所有人工修改记录

### 3.3 历史记录导入

#### 支持格式

| 格式 | 说明 |
|------|------|
| 类型A：扁平表格 | 每行一条完整记录，含日期、客户、产品、物料、用量等 |
| 类型B：固定模板 | 类似纸质版排版的电子版 |

#### 导入步骤

1. 点击导航栏「历史导入」
2. 选择文件（xlsx 或 csv）
3. 选择格式类型
4. 点击「上传并解析」
5. 系统解析后显示暂存记录
6. 检查数据无误后点击「确认导入」
7. 系统自动提取：客户库、产品库、物料库、配方库

#### 注意事项

- CSV 文件请使用 UTF-8 编码保存
- 表头支持中英文（如「日期」或「date」均可识别）
- 空行会自动跳过
- 重复导入相同数据不会创建重复记录

### 3.4 Excel 导出

导出的 Excel 包含 4 个工作表：

| Sheet | 内容 |
|-------|------|
| 生产记录汇总 | 日期、客户、产品、颜色、牌号 |
| 配方明细 | 物料名称、用量、单位、置信度 |
| 识别审查 | 每个字段的 OCR/MiMo 结果、最终值、来源 |
| 导入修正摘要 | 人工修改的字段、旧值、新值、时间 |

---

## 4. 配置说明

### 4.1 模板坐标配置

文件：`app/configs/template_daily_record_v1.yaml`

用于定义表格中各字段的位置坐标。如果表格格式变化，需要修改此配置。

```yaml
template:
  record_blocks:      # 3条记录区域
    - rect: [50, 300, 1750, 800]   # [x1, y1, x2, y2]
  header_fields:      # 表头字段
    - name: "time"
      roi_in_record: [100, 310, 300, 360]
```

### 4.2 OCR 配置

文件：`app/configs/ocr.yaml`

```yaml
ocr:
  engine: "paddleocr"        # OCR 引擎
  confidence_threshold: 0.6  # 置信度阈值
```

### 4.3 MiMo API 配置

文件：`app/configs/mimo.yaml`

```yaml
mimo:
  enabled: true              # 是否启用 MiMo
  mode: "record_level"       # 识别模式
  model: "mimo-v2.5"         # 模型版本
  timeout_seconds: 60        # 超时时间
  max_retry: 2               # 重试次数
  cache_enabled: true        # 是否启用缓存
```

在 `.env` 文件中配置 API Key：
```
MIMO_API_KEY=your_api_key_here
```

### 4.4 单位规则

文件：`app/configs/unit_rules.yaml`

定义可换算单位（g→kg→t）和不可换算单位（包、袋、桶、份）。

### 4.5 导入配置

文件：`app/configs/import_profiles.yaml`

定义导入文件的列映射规则。支持为不同格式的 Excel/CSV 文件配置不同的列名映射。

---

## 5. 常见问题

### Q: 启动后浏览器没有自动打开？

手动访问 http://127.0.0.1:8765

### Q: 上传图片后识别结果为空？

1. 检查图片是否清晰
2. 确认模板坐标配置是否匹配您的表格格式
3. 查看日志文件 `logs/app.log`

### Q: 如何更换 OCR 引擎？

1. 实现 `app/infrastructure/ocr/engine.py` 中的 `OCREngine` 接口
2. 在 `app/infrastructure/ocr/__init__.py` 中注册新引擎
3. 或通过 `set_ocr_engine()` 运行时切换

### Q: 如何接入真实的 MiMo API？

1. 实现 `app/infrastructure/vision/mimo_client.py` 中的 `MimoClient` 接口
2. 在 `.env` 中配置 `MIMO_API_KEY`
3. 在 `app/infrastructure/vision/__init__.py` 中替换为真实客户端

### Q: 数据库在哪里？

SQLite 数据库文件位于 `data/app.sqlite3`

### Q: 上传的图片存储在哪里？

- 原始图片：`data/storage/raw_images/`
- 校正图片：`data/storage/corrected_images/`
- 记录切片：`data/storage/record_crops/`
- 字段切片：`data/storage/cell_crops/`
- 导出文件：`data/storage/exports/`

### Q: 如何备份数据？

备份以下目录即可：
- `data/app.sqlite3`（数据库）
- `data/storage/`（所有图片和导出文件）

### Q: macOS 打包后无法打开？

1. 打开「系统偏好设置 → 安全性与隐私」
2. 点击「仍要打开」允许运行
3. 或右键点击 .app 选择「打开」

### Q: 如何修改服务端口？

编辑 `.env` 文件：
```
APP_PORT=8080
```

---

## 技术支持

如有问题，请提交 Issue 至项目仓库。
