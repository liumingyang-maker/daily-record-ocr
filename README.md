# 每日生产记录智能识别系统

基于 OCR + 视觉大模型的手写生产记录自动识别系统。

> 上传手写表格图片 → 自动识别 → 人工确认 → 导出 Excel

## 功能特性

| 功能 | 说明 |
|------|------|
| 图片识别 | 上传手写生产记录图片，自动校正、切格、OCR 识别、MiMo 大模型复核 |
| 历史导入 | 支持 xlsx/csv 格式的历史电子记录导入，自动提取客户/产品/物料/配方库 |
| 候选融合 | 多来源（OCR、MiMo、历史库、物料字典）候选结果自动融合排序 |
| 人工确认 | 可视化确认页面，支持字段编辑、候选选择、修正日志 |
| Excel 导出 | 一键导出 4 个 Sheet（记录汇总、配方明细、识别审查、修正摘要） |
| 后台设置 | Web 界面配置 API Key、模型参数、服务端口等，无需手动编辑文件 |
| 一键更新 | 设置页面检查更新、查看更新日志、一键拉取最新版本 |
| 跨平台 | 支持 Windows、macOS、Linux |

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Interface 层                          │
│   Web 页面 (Jinja2)    API 路由 (FastAPI)               │
├─────────────────────────────────────────────────────────┤
│                   Application 层                         │
│   上传服务 │ 导入服务 │ 预处理 │ OCR │ MiMo │ 融合 │ 导出 │
├─────────────────────────────────────────────────────────┤
│                    Domain 层                             │
│              物料匹配器 │ 客户匹配器                      │
├─────────────────────────────────────────────────────────┤
│                 Infrastructure 层                        │
│   OpenCV │ PaddleOCR │ MiMo API │ SQLite │ openpyxl     │
├─────────────────────────────────────────────────────────┤
│                    Config 层                             │
│        模板坐标 │ 字段规则 │ OCR/MiMo 参数 │ 导入配置      │
└─────────────────────────────────────────────────────────┘
```

## 核心流程

```
图片上传
   ↓
图像校正（旋转、对比度增强、缩放）
   ↓
模板切格（按 YAML 坐标切割 3 条记录区域）
   ↓
字段切割（每条记录切分时间、客户、物料等字段小格子）
   ↓
OCR 识别（单格文字识别）
   ↓
MiMo 大模型复核（整条记录级识别）
   ↓
历史匹配（与知识库比对）
   ↓
候选融合（多来源排序，置信度分级）
   ↓
人工确认（可视化编辑，修正日志）
   ↓
Excel 导出（4 个 Sheet）
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI + Jinja2 |
| 数据库 | SQLite + SQLAlchemy ORM |
| 图像处理 | OpenCV |
| OCR 引擎 | PaddleOCR（可替换为其他引擎） |
| 视觉大模型 | MiMo API（可替换为其他模型） |
| Excel 导出 | openpyxl |
| 配置管理 | YAML + .env |
| 测试 | pytest (97 个测试用例) |

## 快速开始

### 环境要求

- Python 3.11+
- pip

### 安装运行

**macOS / Linux：**

```bash
# 克隆项目
git clone https://github.com/liumingyang-maker/daily-record-ocr.git
cd daily-record-ocr

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
python3 -m app.main
```

**Windows：**

```cmd
git clone https://github.com/liumingyang-maker/daily-record-ocr.git
cd daily-record-ocr

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

python -m app.main
```

浏览器访问：**http://127.0.0.1:8765**

### 使用启动脚本（推荐）

```bash
# macOS / Linux
./launcher/run.sh

# Windows
launcher\run.bat
```

首次运行会自动创建虚拟环境、安装依赖、启动服务并打开浏览器。

### 更新到最新版本

**方式一：命令行更新（推荐）**

```bash
# macOS / Linux
./launcher/update.sh

# Windows
launcher\update.bat
```

脚本会自动检查远程更新、显示更新内容、确认后拉取代码并安装依赖。

**方式二：Web 页面更新**

启动服务后访问 http://127.0.0.1:8765/settings，点击「检查更新」→「一键更新」。

**方式三：手动更新**

```bash
git pull
pip install -r requirements.txt
```

## 项目结构

```
daily-record-ocr/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── settings.py                # 环境配置
│   ├── configs/                   # YAML 配置文件（8 个）
│   ├── interfaces/                # Interface 层
│   │   ├── web_routes.py          # Web 页面路由
│   │   ├── api_routes.py          # API 路由
│   │   ├── templates/             # Jinja2 模板（7 个页面）
│   │   └── static/                # CSS/JS
│   ├── application/               # Application 层（9 个服务）
│   │   ├── upload_service.py      # 图片上传
│   │   ├── import_service.py      # 历史导入
│   │   ├── preprocess_service.py  # 图像预处理
│   │   ├── ocr_service.py         # OCR 识别
│   │   ├── mimo_service.py        # MiMo 大模型
│   │   ├── fusion_service.py      # 候选融合
│   │   ├── export_service.py      # Excel 导出
│   │   ├── settings_service.py    # 系统设置
│   │   └── update_service.py      # 版本更新
│   ├── domain/                    # Domain 层
│   │   └── matcher.py             # 物料/客户/产品匹配器
│   ├── infrastructure/            # Infrastructure 层
│   │   ├── database/              # SQLAlchemy（20 张表）
│   │   ├── image/                 # OpenCV 图像处理
│   │   ├── ocr/                   # OCR 引擎抽象
│   │   ├── vision/                # MiMo API 抽象
│   │   ├── history_import/        # 文件解析器
│   │   ├── excel/                 # Excel 导出器
│   │   └── storage/               # 文件存储
│   └── tests/                     # 测试（87 个用例）
├── data/                          # 运行时数据
│   ├── storage/                   # 图片/导出文件
│   └── backups/                   # 备份
├── launcher/                      # 启动和打包脚本
│   ├── run.sh / run.bat           # 启动器
│   ├── update.sh / update.bat     # 一键更新
│   ├── install.sh / install.bat   # 依赖安装
│   ├── build_mac.sh               # macOS 打包
│   └── build_windows.bat          # Windows 打包
├── scripts/                       # 工具脚本
├── docs/                          # 设计文档和实现计划
├── README.md                      # 项目说明
├── USAGE.md                       # 使用说明书
└── requirements.txt               # Python 依赖
```

## 配置说明

### Web 设置界面（推荐）

启动服务后访问 **http://127.0.0.1:8765/settings**，可在页面上直接配置：
- MiMo API Key、模型版本、API 地址
- 服务地址、端口、日志级别
- 支持 API 连接测试
- **一键更新**：检查 GitHub 最新版本、查看更新日志、一键拉取并安装依赖

### 环境变量 (.env)

也可以手动编辑 `.env` 文件：

```env
APP_HOST=127.0.0.1
APP_PORT=8765
DATABASE_URL=sqlite:///data/app.sqlite3
MIMO_API_KEY=          # MiMo API Key（可选，不填则使用 mock）
MIMO_MODEL=mimo-v2.5
LOG_LEVEL=INFO
```

### YAML 配置文件

| 文件 | 用途 |
|------|------|
| `template_daily_record_v1.yaml` | 模板坐标（记录区域、字段 ROI） |
| `ocr.yaml` | OCR 引擎参数 |
| `mimo.yaml` | MiMo API 参数 |
| `rules.yaml` | 字段规则和置信度阈值 |
| `unit_rules.yaml` | 单位换算规则 |
| `import_profiles.yaml` | 导入格式列映射 |
| `export_config.yaml` | 导出 Sheet 配置 |
| `app.yaml` | 应用基础配置 |

## 数据库表

系统使用 SQLite，共 20 张表：

| 分类 | 表名 | 说明 |
|------|------|------|
| 识别 | recognition_jobs | 识别任务 |
| | production_records | 生产记录 |
| | record_material_items | 配方明细 |
| | record_machine_params | 机器参数 |
| | record_temperatures | 温度数据 |
| | field_recognition_results | 字段识别结果 |
| | field_candidates | 字段候选值 |
| 知识库 | customers | 客户库 |
| | products | 产品库 |
| | materials | 物料库 |
| | material_aliases | 物料别名 |
| | formulas | 历史配方 |
| | formula_items | 配方明细 |
| 导入 | import_batches | 导入批次 |
| | import_staging_records | 暂存记录 |
| | import_staging_material_items | 暂存物料 |
| | import_staging_warnings | 导入警告 |
| 日志 | manual_correction_logs | 修正日志 |
| | mimo_request_logs | MiMo 请求日志 |
| | mimo_cache | MiMo 缓存 |

## 打包部署

### macOS

```bash
./launcher/build_mac.sh
# 生成: dist/每日生产记录识别系统.app
```

### Windows

```cmd
launcher\build_windows.bat
:: 生成: dist\DailyRecordOCR\
```

## 测试

```bash
# 运行全部测试
python3 -m pytest app/tests/ -v

# 运行特定测试
python3 -m pytest app/tests/test_import_parser.py -v
```

## 扩展指南

### 替换 OCR 引擎

```python
# 实现 OCREngine 接口
from app.infrastructure.ocr.engine import OCREngine, OCRResult

class MyOCREngine(OCREngine):
    def recognize(self, image_path: str) -> OCRResult:
        # 你的 OCR 逻辑
        return OCRResult(text="识别结果", confidence=0.95)

# 注册
from app.infrastructure.ocr import set_ocr_engine
set_ocr_engine(MyOCREngine())
```

### 替换 MiMo 客户端

```python
from app.infrastructure.vision.mimo_client import MimoClient, MimoResult

class MyMimoClient(MimoClient):
    def recognize_record(self, image_path: str) -> MimoResult:
        # 你的 API 调用逻辑
        return MimoResult(fields={...}, success=True)

from app.infrastructure.vision import set_mimo_client
set_mimo_client(MyMimoClient())
```

## 许可证

MIT License
