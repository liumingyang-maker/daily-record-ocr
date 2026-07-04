# 每日生产记录智能识别系统

基于 OCR + 视觉大模型的生产记录自动识别系统，支持手写表格图片识别、历史电子记录导入、人工确认、Excel 导出。

## 功能概览

- **图片识别**：上传手写生产记录图片，自动校正、切格、OCR 识别、MiMo 大模型复核
- **历史导入**：支持 xlsx/csv 格式的历史电子记录导入，自动提取客户/产品/物料/配方库
- **候选融合**：多来源（OCR、MiMo、历史库、物料字典）候选结果自动融合排序
- **人工确认**：可视化确认页面，支持字段编辑、候选选择、修正日志
- **Excel 导出**：一键导出 4 个 Sheet（记录汇总、配方明细、识别审查、修正摘要）
- **跨平台**：支持 Windows 和 macOS

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI + Jinja2 |
| 数据库 | SQLite + SQLAlchemy ORM |
| 图像处理 | OpenCV |
| OCR 引擎 | PaddleOCR（可替换） |
| 视觉大模型 | MiMo API（可替换） |
| Excel 导出 | openpyxl |
| 配置管理 | YAML + .env |
| 测试 | pytest |

## 快速开始

### 环境要求

- Python 3.11+
- pip

### 安装运行

```bash
# 克隆项目
git clone https://github.com/liumingyang-maker/daily-record-ocr.git
cd daily-record-ocr

# 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# 或 .venv\Scripts\activate  # Windows

pip install -r requirements.txt

# 启动服务
python3 -m app.main  # macOS/Linux
# python -m app.main   # Windows
```

浏览器访问 http://127.0.0.1:8765

### 使用启动脚本

**macOS/Linux:**
```bash
./launcher/run.sh
```

**Windows:**
```cmd
launcher\run.bat
```

## 项目结构

```
daily_record_ocr/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── settings.py                # 配置
│   ├── configs/                   # YAML 配置文件
│   ├── interfaces/                # Web 页面 + API 路由
│   │   ├── templates/             # Jinja2 模板
│   │   └── static/                # CSS/JS
│   ├── application/               # 业务服务层
│   │   ├── upload_service.py      # 上传服务
│   │   ├── import_service.py      # 历史导入服务
│   │   ├── preprocess_service.py  # 图像预处理服务
│   │   ├── ocr_service.py         # OCR 识别服务
│   │   ├── mimo_service.py        # MiMo 大模型服务
│   │   ├── fusion_service.py      # 候选融合服务
│   │   └── export_service.py      # Excel 导出服务
│   ├── domain/                    # 领域模型
│   │   └── matcher.py             # 物料/客户匹配器
│   └── infrastructure/            # 基础设施层
│       ├── database/              # SQLAlchemy 模型 + 会话
│       ├── image/                 # OpenCV 图像处理
│       ├── ocr/                   # OCR 引擎抽象
│       ├── vision/                # MiMo API 抽象
│       ├── history_import/        # 文件解析器
│       ├── excel/                 # Excel 导出器
│       └── storage/               # 文件存储
├── data/                          # 数据目录
│   ├── storage/                   # 图片/导出文件
│   └── backups/                   # 备份
├── launcher/                      # 启动和打包脚本
├── scripts/                       # 工具脚本
├── docs/                          # 文档
└── requirements.txt
```

## 配置说明

### 环境变量 (.env)

```env
APP_HOST=127.0.0.1
APP_PORT=8765
DATABASE_URL=sqlite:///data/app.sqlite3
MIMO_API_KEY=          # MiMo API Key（可选）
MIMO_MODEL=mimo-v2.5
LOG_LEVEL=INFO
```

### YAML 配置文件 (app/configs/)

| 文件 | 用途 |
|------|------|
| `app.yaml` | 应用基础配置 |
| `ocr.yaml` | OCR 引擎参数 |
| `mimo.yaml` | MiMo API 参数 |
| `template_daily_record_v1.yaml` | 模板坐标配置 |
| `rules.yaml` | 字段规则和置信度阈值 |
| `unit_rules.yaml` | 单位换算规则 |
| `import_profiles.yaml` | 导入格式配置 |
| `export_config.yaml` | 导出 Sheet 配置 |

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
python -m pytest app/tests/ -v
```

## 许可证

MIT License
