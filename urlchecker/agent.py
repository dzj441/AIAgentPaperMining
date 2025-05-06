import asyncio
import logging
from typing import List, Dict, Any, Optional

from .browser_controller import BrowserController
from .llm_handler import LLMHandler
from .actions import AgentAction, FinishAction, GoToURLAction, GoToURLParams, FinishParams

logger = logging.getLogger(__name__)

class MineAgent:
    def __init__(self, task: str, llm_handler: LLMHandler, start_url: str, headless: bool = True):
        self.task = task
        self.start_url = start_url
        self.llm_handler = llm_handler
        self.browser_controller = BrowserController(headless=headless)
        self.history: List[Dict[str, Any]] = []
        self.max_steps = 10

    async def run(self) -> Optional[FinishParams]:
        logger.info(f"开始执行任务: {self.task}")
        await self.browser_controller.start()
        final_finish_params: Optional[FinishParams] = None

        try:
            logger.info(f"准备跳转到起始网址: {self.start_url}")
            if not self.start_url.startswith(('http://', 'https://')):
                logger.warning(f"起始网址 {self.start_url} 缺少协议头，将自动添加 https://")
                self.start_url = "https://" + self.start_url
            
            initial_action = GoToURLAction(params=GoToURLParams(url=self.start_url))
            init_result = await self.browser_controller.execute_action(initial_action)
            if init_result["status"] == "error":
                logger.error(f"起始网址跳转失败: {init_result['message']}")
                final_finish_params = FinishParams(success=False, message=f"无法打开起始网址: {init_result['message']}")
                return final_finish_params

            for step in range(self.max_steps):
                logger.info(f"--- 开始第 {step + 1}/{self.max_steps} 步 ---")

                logger.debug("准备调用 get_current_state...")
                current_state = await self.browser_controller.get_current_state()
                logger.debug(f"get_current_state 调用完成. URL: {current_state.get('url')}")
                logger.info(f"当前网址: {current_state['url']}")
                logger.debug(f"当前页面元素 (前 500 字符): {str(current_state.get('elements', []))[:500]}...")

                logger.debug("准备调用 llm_handler.get_next_action...")
                llm_response = self.llm_handler.get_next_action(
                    task=self.task,
                    current_state=current_state,
                    history=self.history
                )
                logger.debug(f"llm_handler.get_next_action 调用完成. 返回值: {llm_response}")

                if not llm_response:
                    logger.error("LLM Handler 没有返回有效响应 (返回了 None 或空对象)，Agent 停止。")
                    break

                logger.debug("准备打印 LLM 输出...")
                print("\n-------------------- LLM 输出 --------------------")
                print(f"[想法]: {llm_response.thought}")
                print(f"[动作]: {llm_response.action.action}")
                print(f"[参数]: {llm_response.action.params}")
                print("--------------------------------------------------\n")
                logger.debug("LLM 输出打印完成.")
                
                current_step_history = {"llm_response_raw": llm_response.model_dump_json(indent=2)} 

                action_to_execute = llm_response.action

                if action_to_execute.action == "finish":
                    finish_params = action_to_execute.params
                    logger.info(f"收到结束动作。是否成功: {finish_params.success}。消息: {finish_params.message}")
                    result_message = f"任务结束。是否成功: {finish_params.success}。详情: {finish_params.message}"
                    current_step_history["action_result"] = {"status": "finished", "message": result_message}
                    self.history.append(current_step_history)
                    final_finish_params = finish_params
                    break

                action_result = await self.browser_controller.execute_action(action_to_execute)
                logger.info(f"动作执行结果: {action_result}")
                current_step_history["action_result"] = action_result
                self.history.append(current_step_history)

                if action_result["status"] == "error":
                    logger.warning(f"动作执行失败: {action_result['message']}. 会把这个情况告诉 LLM。")

            else:
                logger.warning(f"Agent 跑满了 {self.max_steps} 步还没结束任务。")
                final_finish_params = FinishParams(success=False, message=f"Agent 超时 ({self.max_steps} 步)")

        except Exception as e:
            logger.exception("Agent 执行过程中出错:")
            final_finish_params = FinishParams(success=False, message=f"Agent 执行出错: {e}")
        finally:
            await self.browser_controller.close()
            logger.info("Agent 运行结束。")
            return final_finish_params 