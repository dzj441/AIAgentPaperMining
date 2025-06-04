import asyncio
import os
import logging
import sys
# 移除 yaml 和 LangChain 相关导入
# import yaml
from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI
# from langchain_community.chat_models import ChatOllama
# from langchain_core.language_models.chat_models import BaseChatModel
from typing import Dict, Any, Optional, Tuple

# 导入新的配置和客户端获取方式
from .config import AI_CONFIG # 直接从 config.py 导入
from .ai_client import get_ai_client, AIClientError # 导入客户端获取函数
from .agent import MineAgent
from .llm_handler import LLMHandler # LLM Handler 仍然使用
# 导入 FinishParams 用于类型提示
from .actions import FinishParams

# 配置日志输出格式
logging.basicConfig(
    level=logging.INFO, # 默认级别可以设为 INFO，减少冗余输出
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# 为 urlchecker 相关模块设置 DEBUG 级别 (如果需要详细日志)
# logging.getLogger('agent').setLevel(logging.DEBUG)
# logging.getLogger('browser_controller').setLevel(logging.DEBUG)
# logging.getLogger('llm_handler').setLevel(logging.DEBUG)
# logging.getLogger('ai_client').setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

# 移除配置加载和基于配置创建 LLM 的函数
# def load_config(path: str = 'config.yaml') -> Dict[str, Any]: ...
# def create_llm_from_config(config: Dict[str, Any]) -> BaseChatModel: ...


# --- 新增的外部调用接口 --- 
async def check_url_is_dataset(url: str) -> Tuple[str, Optional[str]]:
    """
    检查给定的 URL 是否指向一个数据集网站。

    Args:
        url: 要检查的 URL 字符串。

    Returns:
        一个元组 (status: str, thought: Optional[str])
        status: "YES", "NO", 或 "Error: ..."
        thought: 如果 status 是 "YES"，则为 LLM 的思考过程，否则为 None。
    """
    logger.info(f"开始检查 URL: {url}")
    
    # # 定义固定的任务
    # task = "查看该网页是否是数据集的网站，请回答YES或者NO，注意，只回复YES或者NO,不要回答其他内容"
    task = """你是一个专门判断网页是否为“数据集网站”的分类器。请严格按照以下要求执行：

    1. 浏览目标网页，重点关注页面的标题、导航菜单、显著的“数据”“下载”“下载数据”“训练集”“测试集”等字样，以及页面中所有指向数据存储或下载的链接。
    2. 如果页面明确展示了某个数据集的下载链接、数据说明文档、或者有“下载数据”“数据集”“数据集描述”“训练集/验证集/测试集”等关键词，说明它是一个数据集网站；否则说明它不是。
    3. 你只输出“YES”或“NO”，其中
    - “YES” 表示该网页确实是一个数据集网站；
    - “NO” 表示该网页不是数据集网站。
    4. 绝对不要输出任何额外文字，不要解释，不要附加理由，只需输出这两个单词之一。

    示例调用格式（仅供参考，你只需返回 YES 或 NO）：
    User: “https://huggingface.co/datasets/Anthropic/llm_global_opinions”
    Assistant: YES

    User: “https://example.com/blog-post”
    Assistant: NO"""    
    
    # 初始化 LLM Handler
    try:
        llm_handler = LLMHandler()
    except (ValueError, AIClientError) as e:
        error_msg = f"Error: 初始化 LLM Handler 失败: {e}"
        logger.error(error_msg)
        return error_msg, None # 返回 thought 为 None

    # 创建 Agent 实例 (使用无头模式)
    agent = MineAgent(
        task=task,
        llm_handler=llm_handler,
        start_url=url,
        headless=True # 之前是 False，对于接口调用通常应该为 True
    )

    # 运行 Agent 并获取结果
    run_result: Optional[Tuple[FinishParams, Optional[str]]] = await agent.run()

    # 处理结果
    if run_result:
        final_params, thought = run_result # 解包元组
        if final_params:
            if final_params.success:
                # 成功完成，提取 message
                result_message = final_params.message.strip().upper()
                # 确保只返回 YES 或 NO
                if result_message == "YES":
                    logger.info(f"URL '{url}' 的检查结果: YES. Thought: {thought}")
                    return "YES", thought # 返回 YES 和 thought
                elif result_message == "NO":
                    logger.info(f"URL '{url}' 的检查结果: NO.")
                    return "NO", None # NO 的情况下 thought 为 None
                else:
                    # 如果 LLM 没有严格返回 YES/NO
                    warning_msg = f"Warning: LLM 返回了非预期的结果 '{final_params.message}' (期望 YES/NO)，任务视为失败。"
                    logger.warning(warning_msg)
                    # 可以选择返回错误，或者尝试强制判断 (这里选择返回错误)
                    return f"Error: LLM did not return YES or NO ({final_params.message})", None
            else:
                # 任务失败 (由 Agent 内部判断，例如超时或出错)
                error_msg = f"Error: Agent 执行失败: {final_params.message}"
                logger.error(error_msg)
                return error_msg, None
        else:
            # Agent.run 返回了 None (理论上不应该发生，因为我们处理了异常)
            error_msg = "Error: Agent.run() 未返回有效的 final_params。"
            logger.error(error_msg)
            return error_msg, None
    else:
        # Agent.run 返回了 None (理论上不应该发生)
        error_msg = "Error: Agent did not return a result tuple."
        logger.error(error_msg)
        return error_msg, None


# --- 主程序 (现在用于测试新接口) --- 
async def main():
    # 示例 URL 列表
    urls_to_check = [
        # 一个典型的数据集页面
        "https://hf-mirror.com/datasets/OpenGVLab/OmniCorpus-CC-210M", 
        # 一个 GitHub 代码仓库页面
        "https://github.com/langchain-ai/langchain",
        # 一个普通的网站
        "https://www.google.com",
        # 一个可能出错的URL (格式错误)
        "invalid-url-format",
        # 另一个数据集页面
        "https://paperswithcode.com/dataset/imagenet"
    ]

    results_with_thoughts = {}
    for url in urls_to_check:
        status, thought = await check_url_is_dataset(url) # 解包结果
        results_with_thoughts[url] = {"status": status, "thought": thought}
        print(f"\nURL: {url}\nStatus: {status}")
        if thought:
            print(f"Thought: {thought}")
        print("--------------------")
    
    print("\n--- 最终结果汇总 ---")
    for url, res_info in results_with_thoughts.items():
        print(f"{url}: Status - {res_info['status']}, Thought - {res_info['thought']}")


if __name__ == "__main__":
    logger.info("检查 Playwright 浏览器是否安装...")
    # 在脚本开头添加 playwright 安装检查和执行逻辑
    try:
        # 尝试静默运行 playwright install 来确保浏览器已安装
        # 使用 subprocess 来运行命令并捕获输出/错误
        import subprocess
        logger.info("尝试自动安装/更新 Playwright 浏览器驱动...")
        # 对于 Windows, shell=True 可能需要，或者直接指定 playwright.cmd 的完整路径
        # 捕获标准输出和标准错误
        process = subprocess.run([sys.executable, "-m", "playwright", "install"], 
                                 capture_output=True, text=True, check=False, shell=(os.name == 'nt'))
        if process.returncode == 0:
            logger.info("Playwright 浏览器驱动已安装或更新。")
            # print(process.stdout) # 可以取消注释查看安装输出
        else:
            logger.warning(f"Playwright install 命令可能失败 (返回码: {process.returncode})。请手动运行 `playwright install`。错误信息: {process.stderr}")
            # 即使命令失败，也尝试继续运行，Playwright 可能会使用已有的缓存
            # print(process.stdout)
            # print(process.stderr)
    except FileNotFoundError:
        logger.error("错误：找不到 playwright 命令。请确保 Playwright 已安装 (pip install playwright) 并已添加到系统路径，然后手动运行 `playwright install`。")
        sys.exit(1) # 如果 playwright 模块都找不到，则无法继续
    except Exception as install_e:
        logger.error(f"自动安装 Playwright 浏览器时发生错误: {install_e}。请手动运行 `playwright install`。")
        # 继续尝试运行，可能驱动已经存在

    print("开始运行 Agent 检查...")
    asyncio.run(main()) 