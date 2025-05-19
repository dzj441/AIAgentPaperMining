# Paper Mining Pipeline Usage Guide

本工具用于从学术论文（特别是 OpenReview 上的会议论文）中自动挖掘和识别指向数据集或代码仓库的有效链接。

## 1. 环境设置

### 1.1. Python 环境
建议使用 Python 3.8 或更高版本。

### 1.2. 安装依赖
克隆本仓库后，在项目根目录下运行以下命令安装所需依赖：
```bash
pip install -r requirements.txt
```

### 1.3. 安装 Playwright 浏览器驱动
本工具依赖 Playwright 进行部分网页内容的抓取和分析。请运行以下命令安装所需的浏览器驱动：
```bash
playwright install
```
(注意：脚本在首次运行时会尝试自动执行此命令，但手动执行可以确保环境就绪。)

### 1.4. 配置 `urlchecker` 模块 (LLM Agent)
`urlchecker` 模块使用大语言模型 (LLM) 来判断链接是否指向数据集或代码。你需要配置其 API 访问信息。


**直接修改配置文件**
你也可以直接修改 `urlchecker/config.py` 文件中的 `AI_CONFIG` 字典，但这不推荐用于存放 API Key 等敏感信息。

```python
# urlchecker/config.py 中的部分内容
AI_CONFIG = {
    "DEFAULT_AI_SOURCE": "OPENAI", 
    "OPENAI": {
        "API_KEY": os.getenv("OPENAI_API_KEY", "your_default_key_here_if_not_using_env"), 
        "API_BASE": os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1/"), 
        "MODEL": os.getenv("OPENAI_MODEL", "qwen-max"), 
        # ... 其他参数
    },
}
```

## 2. 项目配置文件 (`config.yaml`)
项目的主要行为通过根目录下的 `config.yaml` 文件进行配置。
```yaml
scraper:
  # 存储从 OpenReview API 或 Selenium 抓取到的原始论文页面链接 (JSON 格式) 的目录
  json_dir: "./openreview_paper_links_json" 
  # 下载的 PDF 论文存放的根目录。每个 OpenReview 页面会在此目录下创建一个子目录
  pdf_dir: "./openreview_papers" 
PDFparser:
  # 从 PDF 中提取出的所有 URL 列表的输出文件路径
  output_path: "extracted_urls.txt"
  # 如果为 true, output_path 文件中将只包含一个全局去重的 URL 列表。
  # 如果为 false, URL 会按照其来源 PDF 文件名进行分组。
  flatten : True 
```

## 3. 运行流程

通过 `main.py` 脚本启动整个挖掘流程。

### 3.1. 基本命令
```bash
python main.py [URL1 URL2 ...] [--config <path_to_config.yaml>]
```
*   `[URL1 URL2 ...]`：可选参数。一个或多个 OpenReview 会议页面的 URL。例如，`https://openreview.net/group?id=NeurIPS.cc/2024/Conference#tab-accept-oral`。
*   `--config <path_to_config.yaml>`：可选参数。指定配置文件的路径，默认为项目根目录下的 `config.yaml`。

### 3.2. 示例
```bash
# 处理单个 OpenReview 页面
python main.py "https://openreview.net/group?id=CVPR.cc/2024/Conference#tab-accept"

# 处理多个页面，并使用自定义配置文件
python main.py "URL_A" "URL_B" --config "my_custom_config.yaml"

# 不提供URL，此时脚本的行为依赖于 `pipeline.py` 中的默认设置或配置
python main.py 
```

### 3.3. 流程步骤
1.  **抓取 (Scraping)**: 如果提供了 URL，脚本会尝试从 OpenReview 页面抓取论文的元数据和 PDF 下载链接。
    *   优先使用 OpenReview API。如果 API 失败或未返回结果，则回退到使用 Selenium 进行动态网页抓取。
    *   抓取到的论文链接信息会保存到 `config.yaml` 中 `scraper.json_dir` 指定的目录下的 JSON 文件中。
    *   PDF 文件会下载到 `scraper.pdf_dir` 指定的目录中，并按来源页面分子目录存放。
2.  **PDF 解析 (PDF Parsing)**: 脚本会遍历 `scraper.pdf_dir` 中的 PDF 文件，提取其中包含的所有超链接和文本中出现的 URL。
    *   提取的 URL 会经过初步的域名过滤和替换（例如，`huggingface.co` -> `hf-mirror.com`）。
    *   所有提取并初步处理过的 URL 会保存到 `config.yaml` 中 `PDFparser.output_path` 指定的文件（默认为 `extracted_urls.txt`）。
3.  **链接检查 (Link Checking via LLM Agent)**:
    *   对提取出的链接进行初步的关键词和可访问性过滤。
    *   然后，使用 `urlchecker` 模块中的 LLM Agent (通过 `check_url_is_dataset` 函数) 异步检查每个候选链接，判断其是否指向数据集或代码。
4.  **输出结果**:
    *   Agent 确认的有效数据集/代码链接会打印到控制台。
    *   这些确认的链接也会被保存到项目根目录下的 `final_dataset_links.json` 文件中。

## 4. 输出文件
*   `config.yaml` -> `scraper.json_dir/*.json`: 各个 OpenReview 页面抓取到的论文信息。
*   `config.yaml` -> `scraper.pdf_dir/`: 下载的 PDF 文件。
*   `config.yaml` -> `PDFparser.output_path` (默认 `extracted_urls.txt`): 从 PDF 中提取的原始 URL 列表。
*   `final_dataset_links.json`: 最终由 Agent 确认有效的数据集/代码链接列表。

## 5. 注意事项
*   确保网络连接畅通，特别是对于需要访问外部 API (LLM Agent) 和下载 PDF 的步骤。
*   如果 LLM Agent 使用的是付费 API，请注意监控你的 API 调用消耗。
*   根据你的网络环境，部分 URL (特别是 `github.com` 等) 的访问可能需要代理。代码中包含了一些常见的域名替换逻辑 (如 `github.com` -> `bgithub.xyz`)，你可以在 `PDFparser.py` 中的 `PdfLinkExtractor` 类进一步自定义这些规则。 