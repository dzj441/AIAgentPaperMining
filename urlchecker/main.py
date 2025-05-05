import asyncio
import os
import logging
# 移除 yaml 和 LangChain 相关导入
# import yaml
from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI
# from langchain_community.chat_models import ChatOllama
# from langchain_core.language_models.chat_models import BaseChatModel
from typing import Dict, Any

# 导入新的配置和客户端获取方式
from config import AI_CONFIG # 直接从 config.py 导入
from ai_client import get_ai_client, AIClientError # 导入客户端获取函数
from agent import MineAgent
from llm_handler import LLMHandler # LLM Handler 仍然使用

# 配置日志输出格式
logging.basicConfig(
    level=logging.DEBUG, # 修改: 设置为 DEBUG 级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 移除配置加载和基于配置创建 LLM 的函数
# def load_config(path: str = 'config.yaml') -> Dict[str, Any]: ...
# def create_llm_from_config(config: Dict[str, Any]) -> BaseChatModel: ...


async def main():
    # 加载 .env 文件里的环境变量 (config.py 在导入时已执行)
    # load_dotenv() # config.py 内部已加载
    
    # 检查配置是否正确加载 (可选)
    if not AI_CONFIG:
        logger.error("AI 配置未能加载！请检查 config.py 文件。")
        return
    logger.info(f"使用的 AI 源: {AI_CONFIG.get('DEFAULT_AI_SOURCE')}")

    # --- 配置区 (任务和 URL) ---
    # TODO: 把下面改成你自己的任务和起始网址
    task = "查看该网页是否是数据集的网站，请回答YES或者NO"
    # 修改: 添加 https:// 协议头
    start_url = "https://hf-mirror.com/datasets/OpenGVLab/OmniCorpus-CC-210M"
    
    # 创建 LLM Handler (它内部会调用 get_ai_client)
    try:
        llm_handler = LLMHandler()
    except (ValueError, AIClientError) as e:
        # 捕获客户端初始化或配置相关的错误
        logger.error(f"初始化 LLM Handler 失败: {e}")
        return

    # --- 跑 Agent ---
    # Agent 初始化现在不需要传入 llm 实例，它会使用 LLM Handler
    agent = MineAgent(
        task=task,
        # llm=llm, # 不再需要传递 LLM 实例
        llm_handler=llm_handler, # 传递 Handler 实例
        start_url=start_url,
        headless=False # True 就是无头模式，False 会打开浏览器窗口让你看着它操作
    )
    # 注意: MineAgent 的 run 和 step 需要适配同步的 get_next_action
    # 我们需要修改 MineAgent 来调用同步方法或将 get_next_action 改回异步并使用异步 client
    # 为了保持与 sql 示例一致 (同步 complete), 我们需要调整 Agent 的调用方式
    # 或者，更简单的做法是允许 Agent 的主循环是异步的，但在调用 LLM 时阻塞等待同步结果。
    # 当前 MineAgent.run 已经是 async，所以它可以 await 异步操作，但调用 llm_handler.get_next_action 时会是同步阻塞。
    # 这通常没问题，因为 IO 密集型操作（浏览器交互）仍然是异步的。
    await agent.run()

if __name__ == "__main__":
    # 运行前，确认 Playwright 的浏览器驱动已经装好了
    # 在终端里敲这个命令: playwright install
    logger.info("检查 Playwright 浏览器是否安装...")
    # 这里只是打印个提示，没做实际检查或自动安装
    # 如果需要可以加代码来检查 playwright list-browsers 的输出，或者直接运行 playwright install
    print("\n请确保你已经在终端运行过 `playwright install` 来安装浏览器驱动。")
    print("开始运行 Agent...")

    # 跑异步的 main 函数
    asyncio.run(main()) 