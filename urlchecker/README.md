# mineAgent - 一个简单的 AI 网页操作代理

`mineAgent` 是一个概念验证项目，演示了如何利用大型语言模型 (LLM) 来理解用户指令，并通过 Playwright 控制浏览器来执行网页操作任务。

## 主要特点

*   **LLM 驱动**: 使用 LLM (如 OpenAI GPT 或本地运行的 Ollama 模型) 来分析网页状态并决定下一步操作。
*   **配置灵活**: 通过 `config.yaml` 文件轻松切换和配置不同的 LLM 提供商 (OpenAI, Siliflow/兼容 API, Ollama)。
*   **浏览器自动化**: 使用 Playwright 执行实际的浏览器交互（导航、点击、输入、提取信息）。
*   **逐步输出**: 清晰地打印出 LLM 在每一步的思考过程 (`thought`) 和决策的动作 (`action`)，方便调试和理解。
*   **结构化信息提取**: 从网页提取关键元素（链接、按钮、输入框等）的结构化信息，提供给 LLM 作为决策依据。

## 安装与设置

请按照以下步骤设置和准备运行 `mineAgent`：

**1. 准备环境:**

*   确保你安装了 Python (推荐 3.10 或更高版本)。
*   拥有一个终端或命令行工具。

**2. 获取代码:**

*   将 `mineAgent` 文件夹下载或克隆到你的本地机器。

**3. 进入项目目录:**

*   在终端中，使用 `cd` 命令进入 `mineAgent` 文件夹。
    ```bash
    cd path/to/your/mineAgent
    ```

**4. 安装依赖库:**

*   运行以下命令安装所有必需的 Python 包（现在包含 `requests` 和 `sseclient`，移除了 LangChain）：
    ```bash
    pip install -r requirements.txt
    ```

**5. 安装浏览器驱动:**

*   Playwright 需要浏览器驱动来控制浏览器。运行以下命令安装（主要是 Chromium）：
    ```bash
    playwright install
    ```
    *(这个命令通常只需要运行一次)*

**6. 配置 LLM (config.py):**

*   打开 `mineAgent/config.py` 文件。
*   **选择 AI 源**: 修改 `AI_CONFIG["DEFAULT_AI_SOURCE"]` 的值为 `"OPENAI"` (或者未来支持的其他源)。
*   **配置参数**: 查看 `AI_CONFIG["OPENAI"]` (或其他源) 下的配置：
    *   `API_KEY`: 确认它指向正确的环境变量名（如 `OPENAI_API_KEY`），或者直接在此处设置 Key (不推荐)。
    *   `API_BASE`: 如果使用标准 OpenAI，通常无需修改。如果使用 **Siliflow 或本地 OpenAI 兼容 API**，必须将其修改为你的服务地址 (例如 `"https://api.siliconflow.cn"` 或 `"http://localhost:8000/v1"`)。也可以通过设置 `OPENAI_API_BASE` 环境变量来覆盖。
    *   `MODEL`: 设置你想使用的模型名称 (例如 `"gpt-3.5-turbo"` 或 Siliflow 提供的模型名)。也可以通过 `OPENAI_MODEL` 环境变量覆盖。
    *   可以调整 `TEMPERATURE` 和 `MAX_TOKENS`。

**7. 设置 API Keys (.env):**

*   将 `.env.example` 文件**重命名**为 `.env`。
*   用文本编辑器打开 `.env` 文件。
*   **根据 `config.py` 中 `API_KEY` 配置指向的环境变量名**，填入必要的 API Key。例如：
    *   如果 `config.py` 中 `API_KEY` 配置为 `os.getenv("OPENAI_API_KEY", ...)`，则你**必须**在 `.env` 文件中设置 `OPENAI_API_KEY=sk-xxxxxxxx...`。
    *   类似地，根据需要设置 `OPENAI_API_BASE` 和 `OPENAI_MODEL` 环境变量来覆盖 `config.py` 中的默认值。

## 如何运行

**1. (可选) 自定义任务:**

*   打开 `mineAgent/main.py` 文件。
*   修改 `task` 变量为你希望代理执行的任务描述。
*   修改 `start_url` 变量为代理开始访问的网址。

**2. (可选) 显示浏览器窗口:**

*   默认不显示浏览器窗口 (无头模式)。
*   如果想观看操作过程，在 `mineAgent/main.py` 中找到 `MineAgent` 的初始化部分，将 `headless=True` 改为 `headless=False`。

**3. 启动代理:**

*   确保你的终端位于 `mineAgent` 文件夹内。
*   运行以下命令：
    ```bash
    python main.py
    ```

**4. 查看输出:**

*   终端会显示运行日志，包括代理启动、导航、步骤执行等。
*   在每个步骤中，会打印出 **LLM 的思考过程和决策**：
    ```
    -------------------- LLM 输出 --------------------
    [想法]: [LLM 的分析和推理]
    [动作]: [LLM 选择的动作名称]
    [参数]: [动作所需的参数]
    --------------------------------------------------
    ```
*   代理会持续运行，直到任务完成 (收到 `finish` 动作)、达到最大步数限制 (默认为 10) 或遇到严重错误。

## 工作原理简述

`mineAgent` 的核心是一个循环：

1.  **获取状态**: 使用 Playwright 获取当前网页的 URL、标题以及页面上的关键可见元素列表（包含标签、文本、属性）。
2.  **LLM 决策**: 将当前状态、用户任务和之前的操作历史发送给配置好的 LLM。
3.  **解析动作**: LLM 返回一个包含其思考过程 (`thought`) 和下一步动作 (`action`) 的 JSON 响应。程序解析并验证这个响应。
4.  **执行动作**: 使用 Playwright 执行 LLM 决定的动作（如跳转、点击、输入）。
5.  **记录历史**: 将 LLM 的响应和动作执行结果记录下来，用于下一步的 LLM 调用。
6.  **重复**: 回到步骤 1，直到任务完成或达到停止条件。

## 注意事项与未来改进

*   **元素提取**: 当前的元素提取 (`browser_controller.py` 中的 `get_current_state`) 虽然比之前版本详细，但仍有改进空间。例如，可以提取更复杂的元素关系、优化可见性判断、或根据任务动态调整提取范围。
*   **CSS 选择器**: 目前 LLM 需要根据提取到的元素信息（ID、文本、属性）自行推断出合适的 CSS 选择器来执行点击或输入操作。这可能不够精确，未来可以考虑让 LLM 直接引用元素 ID，由代码转换为 Playwright Locator。
*   **错误处理**: 错误处理相对基础，可以进一步增强鲁棒性。
*   **记忆机制**: 当前没有长效记忆机制。
*   **提示工程**: 系统提示 (`prompts.py`) 可以根据具体任务和 LLM 的特性进行优化。 