# 手写生产记录识别工具（轻量版）

把手机拍摄的手写笔记交给任意视觉模型，得到可人工修正的结构化 JSON，再写入固定 Excel 文档。

> 默认流程：多图上传 → 自动旋转/缩放 → 整图视觉理解 → JSON Schema 校验 → 浏览器人工确认 → Excel 模板映射

## 为什么改成轻量版

原实现针对“固定印刷表格”设计：先把图片统一缩放，再按固定坐标切出 3 个记录区和多个字段小格，随后分别调用 OCR 和 MiMo。你提供的实际图片是自由排版的横线笔记，原料名、数量和“工艺”区域依靠空间关系对应，固定坐标切格很容易把内容切错，也会丢掉上下文。

轻量版做了这些取舍：

- 不再使用 MiMo，也不绑定任何厂商模型。
- 默认不使用 PaddleOCR、OpenCV、SQLAlchemy、Alembic。
- 整张图片或多张图片一次交给视觉模型，保留手写内容的空间关联。
- 用 `config/record_schema.yaml` 定义识别字段和提示词。
- 用 `config/export.yaml` 定义固定 Excel 的单元格与表格映射。
- 每个任务只保存一个目录和几个 JSON/图片文件，不使用数据库。
- 保留旧 `app/` 代码作为参考，但默认入口切换到 `lite_app`。

## 项目结构

```text
lite_app/
├── main.py          # FastAPI 页面和接口
├── pipeline.py      # 图片 → 模型 → JSON → 校验
├── providers.py     # 可替换视觉模型适配器
├── exporter.py      # 固定 Excel 模板映射
├── image_utils.py   # Pillow 旋转与缩放
├── storage.py       # 文件夹 + JSON 存储
└── templates/       # 两个简单页面
config/
├── app.yaml         # 应用和模型配置
├── record_schema.yaml
├── export.yaml
└── mock_result.json
```

## 快速开始

Python 3.11+：

```bash
git clone https://github.com/liumingyang-maker/daily-record-ocr.git
cd daily-record-ocr
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

浏览器打开 `http://127.0.0.1:8765`。默认使用 `mock`，无需 API 即可测试上传、人工修正和 Excel 导出。

原启动脚本仍可使用：

```bash
./launcher/run.sh        # macOS / Linux
launcher\run.bat         # Windows
```

## 接入任意视觉模型

复制环境变量示例：

```bash
cp .env.example .env
```

然后设置：

```env
VISION_PROVIDER=openai_compatible
VISION_BASE_URL=http://127.0.0.1:11434/v1
VISION_ENDPOINT=/chat/completions
VISION_API_KEY=
VISION_MODEL=qwen2.5-vl:7b
```

当前内置的是 OpenAI-compatible Chat Completions 适配器。很多本地服务和云端服务都可通过兼容接口接入。服务端不支持 `response_format=json_schema` 时，保持 `config/app.yaml` 中 `use_json_schema: false`；Schema 仍会放进提示词，返回后再由本地校验。

### 接入非兼容接口

只需实现一个类：

```python
from pathlib import Path
from typing import Any
from lite_app.providers import VisionProvider

class MyVisionProvider(VisionProvider):
    async def analyze(
        self,
        image_paths: list[Path],
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> str:
        # 调用你的模型，并返回包含 JSON 的文本
        return '{"page_heading":"", "records":[], "warnings":[]}'
```

然后在 `lite_app/providers.py` 的 `build_provider()` 中注册一个名称即可。业务流程、页面和 Excel 导出都无需修改。

## 按你的手写格式调整字段

编辑 `config/record_schema.yaml`。默认 Schema 针对你给出的笔记结构：

- 页面标题或人名 `page_heading`
- 多条记录 `records`
- 每条记录的日期、配方/产品标题
- 原料名称与数量 `materials`
- “工艺”参数 `process_parameters`
- 备注、整体置信度和不确定项

提示词特别要求模型按“原料名称行”和“下方数量行”的水平位置配对，避免数量串位。看不清时返回空字符串和 warning，不允许凭经验补写。

## 写入固定 Excel 文档

### 直接生成工作簿

默认 `config/export.yaml` 会生成：

1. `记录汇总`
2. `配方明细`
3. `工艺参数`

### 写入你已有的固定模板

把模板放到项目中，例如：

```text
config/my_fixed_template.xlsx
```

然后修改：

```yaml
excel:
  template_path: config/my_fixed_template.xlsx
```

固定单元格：

```yaml
cells:
  - sheet: 记录汇总
    cell: B1
    value: "$root.page_heading"
```

重复表格：

```yaml
tables:
  - sheet: 配方明细
    source: records
    expand: materials
    start_row: 6
    include_header: false
    columns:
      - column: A
        value: "$parent_index"
      - column: B
        value: "$parent.record_date"
      - column: C
        value: name
      - column: D
        value: amount
```

可用表达式：

- `$index`：当前列表序号
- `$parent_index`：所属记录序号
- `$root.page_heading`：顶层字段
- `$parent.record_date`：父记录字段
- `name`：当前材料或工艺项字段
- `literal:固定文字`：固定值

这样模型输出格式和最终文档布局完全解耦，换模型、换提示词、换 Excel 模板都不用改主流程代码。

## 图片方向

你给出的示例是手机竖图，但正文需要逆时针 90° 才能正常阅读。默认上传选项会：

1. 应用 EXIF 方向；
2. 如果仍是竖图，逆时针 90° 转为横图；
3. 最长边缩放到 2048 像素。

上传页面也可明确选择不旋转、顺时针、逆时针或 180°。

## 数据目录

每个任务保存在：

```text
data/jobs/<任务号>/
├── job.json
├── source_*.jpg
├── prepared_*.jpg
├── raw_response.txt
├── result.json
└── recognized-<任务号>.xlsx
```

无需数据库。备份整个 `data/jobs` 即可迁移。

## 旧版代码

旧的分层实现仍位于 `app/`，其完整依赖保存在 `requirements-legacy.txt`。轻量版默认入口通过 `app/main.py` 转发到 `lite_app.main`，日常使用无需安装旧依赖。

## 测试

```bash
pip install -r requirements-dev.txt
pytest
```
