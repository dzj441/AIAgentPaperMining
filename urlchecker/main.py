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
from typing import Dict, Any, Optional

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


async def check_url_likely_dataset(url: str) -> str:
    logger.info(f"开始初步检查疑似数据集网站 URL: {url}")
    task = "查看该网站是否疑似是数据集的网站(访问不了算作疑似), 仅回答YES、MAYBE或者NO, 注意, 只回复YES、MAYBE或者NO, 不要回答其他内容"
    try:
        llm = LLMHandler()
    except(ValueError, AIClientError) as e:
        error_msg = f"Error: 初始化判断疑似数据集的LLM失败: {e}"
        logger.error(error_msg)
        return error_msg
    agent = MineAgent(
        task = task,
        llm_handler = llm,
        start_url = url,
        headless = True
    )
    final_params: Optional[FinishParams] = await agent.run()
    if final_params:
        if final_params.success:
            result = final_params.message.strip().upper()
            if result in ["YES", "MAYBE", "NO"]:
                logger.info(f"URL '{url}' 的检查结果: {result}")
                return result
            else:
                warning_msg = f"Warning: LLM 返回了非预期的结果 '{final_params.message}'，任务视为失败。"
                logger.warning(warning_msg)
                return f"Error: LLM did not return YES, MAYBE, or NO ({final_params.message})"
        else:
            error_msg = f"Error: Agent 执行失败: {final_params.message}"
            logger.error(error_msg)
            return error_msg
    else:
        error_msg = "Error: Agent did not return a final result."
        logger.error(error_msg)
        return error_msg
    

async def check_url_likely_dataset(url: str) -> str:
    logger.info(f"开始初步检查疑似数据集网站 URL: {url}")
    task = "查看该网站是否疑似是数据集的网站(访问不了算作疑似), 仅回答YES、MAYBE或者NO, 注意, 只回复YES、MAYBE或者NO, 不要回答其他内容"
    try:
        llm = LLMHandler()
    except(ValueError, AIClientError) as e:
        error_msg = f"Error: 初始化判断疑似数据集的LLM失败: {e}"
        logger.error(error_msg)
        return error_msg
    agent = MineAgent(
        task = task,
        llm_handler = llm,
        start_url = url,
        headless = True
    )
    final_params: Optional[FinishParams] = await agent.run()
    if final_params:
        if final_params.success:
            result = final_params.message.strip().upper()
            if result in ["YES", "MAYBE", "NO"]:
                logger.info(f"URL '{url}' 的检查结果: {result}")
                return result
            else:
                warning_msg = f"Warning: LLM 返回了非预期的结果 '{final_params.message}'，任务视为失败。"
                logger.warning(warning_msg)
                return f"Error: LLM did not return YES, MAYBE, or NO ({final_params.message})"
        else:
            error_msg = f"Error: Agent 执行失败: {final_params.message}"
            logger.error(error_msg)
            return error_msg
    else:
        error_msg = "Error: Agent did not return a final result."
        logger.error(error_msg)
        return error_msg
    

async def check_url_no_maybe_dataset(url: str) -> str:
    logger.info(f"开始初步检查不算作数据集网站 URL: {url}")
    task = "查看该网站是否疑似是数据集的网站(访问不了算作疑似), 仅回答YES、MAYBE或者NO, 注意, 只回复YES、MAYBE或者NO, 不要回答其他内容"
    try:
        llm = LLMHandler()
    except(ValueError, AIClientError) as e:
        error_msg = f"Error: 初始化判断疑似数据集的LLM失败: {e}"
        logger.error(error_msg)
        return error_msg
    agent = MineAgent(
        task = task,
        llm_handler = llm,
        start_url = url,
        headless = True
    )
    final_params: Optional[FinishParams] = await agent.run()
    if final_params:
        if final_params.success:
            result = final_params.message.strip().upper()
            if result in ["YES", "MAYBE", "NO"]:
                logger.info(f"URL '{url}' 的检查结果: {result}")
                return result
            else:
                warning_msg = f"Warning: LLM 返回了非预期的结果 '{final_params.message}'，任务视为失败。"
                logger.warning(warning_msg)
                return f"Error: LLM did not return YES, MAYBE, or NO ({final_params.message})"
        else:
            error_msg = f"Error: Agent 执行失败: {final_params.message}"
            logger.error(error_msg)
            return error_msg
    else:
        error_msg = "Error: Agent did not return a final result."
        logger.error(error_msg)
        return error_msg


# --- 新增的外部调用接口 --- 
async def check_url_is_dataset(url: str) -> str:
    """
    检查给定的 URL 是否指向一个数据集网站。

    Args:
        url: 要检查的 URL 字符串。

    Returns:
        "YES" 或 "NO" (基于 LLM 的判断)，或者返回 "Error: ..." 如果过程中出错。
    """
    logger.info(f"开始检查 URL: {url}")
    
    # 定义固定的任务
    task = "查看该网页是否是数据集的网站，请回答YES或者NO，注意，只回复YES或者NO,不要回答其他内容"
    
    # 初始化 LLM Handler
    try:
        llm_handler = LLMHandler()
    except (ValueError, AIClientError) as e:
        error_msg = f"Error: 初始化 LLM Handler 失败: {e}"
        logger.error(error_msg)
        return error_msg

    # 创建 Agent 实例 (使用无头模式)
    agent = MineAgent(
        task=task,
        llm_handler=llm_handler,
        start_url=url,
        headless=True # 接口调用通常不需要显示浏览器
    )

    # 运行 Agent 并获取结果
    final_params: Optional[FinishParams] = await agent.run()

    # 处理结果
    if final_params:
        if final_params.success:
            # 成功完成，提取 message
            result = final_params.message.strip().upper()
            # 确保只返回 YES 或 NO
            if result == "YES" or result == "NO":
                 logger.info(f"URL '{url}' 的检查结果: {result}")
                 return result
            else:
                 # 如果 LLM 没有严格返回 YES/NO
                 warning_msg = f"Warning: LLM 返回了非预期的结果 '{final_params.message}'，任务视为失败。"
                 logger.warning(warning_msg)
                 # 可以选择返回错误，或者尝试强制判断 (这里选择返回错误)
                 return f"Error: LLM did not return YES or NO ({final_params.message})"
        else:
            # 任务失败 (由 Agent 内部判断，例如超时或出错)
            error_msg = f"Error: Agent 执行失败: {final_params.message}"
            logger.error(error_msg)
            return error_msg
    else:
        # Agent.run 返回了 None (理论上不应该发生，因为我们处理了异常)
        error_msg = "Error: Agent did not return a final result."
        logger.error(error_msg)
        return error_msg


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

    results = {}
    for url in urls_to_check:
        result = await check_url_is_dataset(url)
        results[url] = result
        print(f"\nURL: {url}\nResult: {result}\n{'-'*20}")
    
    print("\n--- 最终结果汇总 ---")
    for url, result in results.items():
        print(f"{url}: {result}")


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