# URLChecker 项目介绍

本mardown文档旨在介绍 `URLChecker` 项目的功能、工作流程和核心组件的实现原理。

## 1. 项目功能

`URLChecker` 是一个基于 AI Agent 的工具，其核心功能是判断给定的 URL 是否指向一个数据集的网站。

它通过模拟用户使用浏览器访问网页，并利用大语言模型 (LLM) 分析网页内容，最终给出一个 "YES" 或 "NO" 的判断。

## 2. 工作流程

项目的主要工作流程由 `main.py` 中的 `check_url_is_dataset(url: str)` 函数驱动：

1.  **初始化**:
    *   接收一个待检查的 `url` 作为输入。
    *   定义一个固定的任务指令给 LLM："查看该网页是否是数据集的网站，请回答YES或者NO，注意，只回复YES或者NO,不要回答其他内容"。
    *   初始化 `LLMHandler`：`LLMHandler` 负责与配置的 AI 大语言模型进行通信。它会从 `config.py` 加载 AI 模型的 API 地址、密钥和模型名称等配置。
    *   创建 `MineAgent` 实例：`MineAgent` 是核心的智能代理，它接收任务描述、`LLMHandler` 实例、起始 `url` 以及是否以无头模式运行浏览器的配置（在此接口中默认为无头模式）。

2.  **Agent 执行**:
    *   调用 `agent.run()` 方法开始执行任务。
    *   **浏览器启动**: `MineAgent`内部的 `BrowserController` 会启动一个 Playwright控制的浏览器实例 (默认为 Chromium)。
    *   **初始导航**: Agent 首先尝试导航到用户提供的 `start_url`。如果 URL 无效或无法访问，则直接返回错误。
    *   **迭代决策与行动 (Agent Loop)**: Agent 进入一个循环，最多执行预设的步数 (默认为 10 步)：
        *   **获取当前状态**: `BrowserController` 提取当前浏览器页面的信息，包括当前 URL、页面标题以及页面上可交互和重要的文本元素 (如链接、按钮、输入框、标题、段落等)。每个元素会被赋予一个临时 ID，并提取其标签名、文本内容和相关属性。
        *   **LLM 交互**: `LLMHandler` 将当前任务、当前页面状态 (包含元素列表) 和之前的交互历史 (如果存在) 组装成一个提示 (prompt)，发送给大语言模型。系统提示 (`prompts.py`) 会指导 LLM 如何分析信息并以特定的 JSON 格式返回其决策。
        *   **LLM 响应**: LLM 返回一个 JSON 对象，包含两部分：
            *   `thought`: LLM 的思考过程，解释它为什么选择下一步的动作。
            *   `action`: LLM 建议执行的具体动作，例如：
                *   `goto_url`: 跳转到新的 URL。
                *   `click_element`: 点击页面上的某个元素 (通过 CSS 选择器定位)。
                *   `type_text`: 在某个输入框中输入文本。
                *   `extract_info`: 提取特定元素的信息 (目前该项目中主要用于隐式的内容理解，最终由 `finish` 动作的 `message` 体现判断)。
                *   `finish`: 结束任务，并提供结果 (成功/失败以及一条消息)。
        *   **动作执行**: `BrowserController` 根据 LLM 返回的 `action` 来操作浏览器。例如，如果 LLM 指示点击一个链接，`BrowserController` 会使用 Playwright 找到并点击该链接。
        *   **历史记录**: LLM 的响应和动作的执行结果会被记录下来，作为下一步 LLM 决策的上下文。
        *   **循环与终止**: 这个"获取状态 -> LLM 决策 -> 执行动作"的循环会持续进行，直到 LLM 返回 `finish` 动作，或者达到最大执行步数。

3.  **结果处理**:
    *   `agent.run()` 返回 `FinishParams` 对象，其中包含任务是否成功 (`success`) 以及 LLM 给出的最终消息 (`message`)。
    *   `check_url_is_dataset` 函数会检查 `message` 是否严格为 "YES" 或 "NO"。
        *   如果 LLM 返回 "YES" 或 "NO"，则该字符串作为最终结果返回。
        *   如果 LLM 返回其他内容，或者 Agent 执行失败/超时，则返回相应的错误信息。

4.  **浏览器关闭**: 在 `agent.run()` 结束时 (无论成功与否)，`BrowserController` 都会确保关闭浏览器。

## 3. 核心组件原理

### 3.1. `MineAgent` (`agent.py`)

*   **角色**: 任务的总协调者和执行者。
*   **机制**:
    *   维护一个与 LLM 的交互循环，通过 `LLMHandler` 获取决策，通过 `BrowserController` 执行决策。
    *   管理交互历史 (`self.history`)，为 LLM 提供上下文。
    *   设定最大执行步数 (`self.max_steps`) 防止无限循环。
    *   处理任务的启动 (导航到初始 URL) 和结束 (超时或 LLM 发出 `finish` 指令)。

### 3.2. `BrowserController` (`browser_controller.py`)

*   **角色**: 浏览器的实际控制者，封装了 Playwright 的底层操作。
*   **机制**:
    *   **启动与关闭**: 管理 Playwright 实例、浏览器对象和页面对象。
    *   **状态提取 (`get_current_state`)**:
        *   获取当前 URL 和标题。
        *   通过一组预定义的 CSS 选择器 (如 `a`, `button`, `input`, `h1`, `p` 等) 查找页面上的可见元素。
        *   对每个元素提取标签名、内部文本 (限制长度并清理)、常用属性 (如 `href`, `aria-label`, `placeholder`)，并为其分配一个临时 ID。
        *   返回一个包含页面信息和元素列表的字典，供 LLM 分析。
    *   **动作执行 (`execute_action`)**:
        *   接收 `AgentAction` 对象 (由 LLM 决定)。
        *   根据动作类型 (如 `goto_url`, `click_element`, `type_text`) 调用相应的 Playwright 函数来操作浏览器。
        *   包含超时处理，防止单个操作卡死。
        *   返回动作的执行结果 (成功/失败及消息)。

### 3.3. `LLMHandler` (`llm_handler.py`)

*   **角色**: 与大语言模型 (LLM) 的通信接口。
*   **机制**:
    *   **初始化**: 从 `config.py` 获取 AI 客户端 (`AIClient`)，并加载系统提示 (`prompts.py`)。
    *   **消息构建 (`_construct_messages`)**:
        *   将系统提示、历史交互记录、当前任务描述和当前浏览器页面状态（由 `BrowserController` 提供）组合成发送给 LLM 的消息列表。
    *   **获取下一动作 (`get_next_action`)**:
        *   调用 `AIClient.complete()` 方法，将构建好的消息发送给 LLM。
        *   接收 LLM 返回的文本响应。
        *   清理并解析 LLM 返回的 JSON 字符串。
        *   使用 Pydantic 模型 (`LLMResponse` from `actions.py`) 验证 JSON 结构的正确性。
        *   处理 LLM 调用失败、JSON 解析错误或结构验证失败等异常，并返回一个表示任务失败的 `FinishAction`。

### 3.4. `AIClient` (`ai_client.py`) & `config.py`

*   **`config.py`**:
    *   存储 AI 服务的配置，如 API Key、API Base URL、模型名称、温度等。
    *   使用 `dotenv` 从 `.env` 文件加载环境变量，实现配置与代码分离。
    *   `AI_CONFIG` 字典是主要的配置源，支持通过 `DEFAULT_AI_SOURCE` 切换不同的 AI 服务配置 (目前主要使用 `OPENAI` 兼容配置，指向阿里云 Dashscope)。
*   **`AIClient`**:
    *   定义了与 AI 服务交互的客户端基类。
    *   `OpenAIClient` 是其具体实现，负责向 OpenAI 兼容的 API (如 `config.py` 中配置的 Dashscope 地址) 发送 HTTP 请求。
    *   `complete()` 方法构造请求体 (包含模型、消息列表、温度等)，发送请求，并处理响应，提取 LLM 的回复内容。
    *   包含错误处理和响应验证逻辑。
    *   `get_ai_client()` 是一个工厂函数，根据 `config.py` 的设置创建并返回具体的 AI 客户端实例。

### 3.5. `Actions` (`actions.py`)

*   **角色**: 使用 Pydantic 定义 LLM 期望的响应结构以及 Agent 可以执行的各种动作及其参数的数据模型。
*   **机制**:
    *   **参数模型**: 如 `GoToURLParams`, `ClickElementParams`, `FinishParams` 等，明确了每个动作需要哪些输入。
    *   **动作模型**: 如 `GoToURLAction`, `ClickElementAction`, `FinishAction` 等，将动作名称 (一个字面量) 与其参数模型绑定。
    *   `AgentAction`: 一个 `Union` 类型，聚合了所有可能的动作模型，代表 LLM 可以选择的动作集合。
    *   `LLMResponse`: 定义了 LLM 响应的顶层结构，必须包含 `thought` (字符串，LLM的思考过程) 和 `action` (一个 `AgentAction` 实例)。这是 LLM 输出必须严格遵守的格式。

### 3.6. `Prompts` (`prompts.py`)

*   **角色**: 定义了指导 LLM 行为的系统提示 (System Prompt)。
*   **机制**:
    *   `MANUAL_LLMRESPONSE_SCHEMA`: 一个核心部分，是手动编写的 JSON Schema，详细定义了 `LLMResponse` 的结构，包括所有可能的 `action` 及其参数。这个 Schema 会被嵌入到系统提示中，告诉 LLM 必须如何格式化其输出。
    *   `SYSTEM_PROMPT_TEMPLATE`: 包含了对 LLM 的总体指示、任务目标、输入信息描述、以及最重要的——强制要求 LLM 以特定 JSON 格式 (`MANUAL_LLMRESPONSE_SCHEMA` 指定的格式) 进行响应。
    *   `get_system_prompt()`: 将 `MANUAL_LLMRESPONSE_SCHEMA` 插入到模板中，生成最终发送给 LLM 的完整系统提示。

## 4. 运行前准备

*   **Python 环境**: 需要 Python 运行环境。
*   **依赖安装**: 通过 `pip install -r requirements.txt` 安装所需依赖包，主要包括 `playwright`, `python-dotenv`, `requests`, `sseclient`, `pydantic`。
*   **Playwright 浏览器驱动**: 首次运行时，或 `main.py` 脚本在执行前会尝试自动运行 `playwright install` 来安装所需的浏览器驱动 (如 Chromium)。如果自动安装失败，需要手动执行该命令。
*   **`.env` 文件配置**:
    *   在项目根目录下创建一个 `.env` 文件 (可以从 `.env.example` 复制)。
    *   至少需要配置以下与 AI 服务相关的环境变量 (如果不想使用 `config.py` 中的硬编码默认值)：
        *   `OPENAI_API_KEY`: 你的 AI 服务 API 密钥。
        *   `OPENAI_API_BASE`: AI 服务的 API 基础 URL。
        *   `OPENAI_MODEL`: 使用的 AI 模型名称。
