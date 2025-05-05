import json
import logging
from typing import List, Dict, Any, Optional

# 移除 LangChain 相关的导入
# from langchain_core.language_models.chat_models import BaseChatModel
# from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pydantic import ValidationError

# 导入新的 AI Client
from ai_client import AIClient, AIClientError, get_ai_client
from actions import LLMResponse, AgentAction, FinishAction, FinishParams
from prompts import get_system_prompt # 系统提示仍然需要

logger = logging.getLogger(__name__)

class LLMHandler:
    # 不再需要传入 llm 实例，改为使用全局的 ai_client 或按需获取
    # def __init__(self, llm: BaseChatModel):
    def __init__(self):
        # 获取根据配置创建的 AI Client 实例
        self.client: AIClient = get_ai_client() 
        self.system_prompt = get_system_prompt()
        # 从 client 获取一些配置可能有用，或者直接从 AI_CONFIG 读取
        # 例如，获取模型名称以传递给 complete 方法 (如果需要覆盖客户端默认值)
        from config import AI_CONFIG
        default_source = AI_CONFIG.get("DEFAULT_AI_SOURCE", "OPENAI")
        self.default_model = AI_CONFIG.get(default_source, {}).get('MODEL')
        self.default_temperature = AI_CONFIG.get(default_source, {}).get('TEMPERATURE', 0.0)
        self.default_max_tokens = AI_CONFIG.get(default_source, {}).get('MAX_TOKENS', 1024)

    def _construct_messages(self, task: str, current_state: Dict[str, Any], history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """组装要发给 LLM 的消息列表 (返回 OpenAI 格式的字典列表)。"""
        messages = [{"role": "system", "content": self.system_prompt}]

        # 把历史记录加进去
        for entry in history:
            # AI 上一步的想法和动作 (原始 JSON 字符串)
            if "llm_response_raw" in entry:
                # 注意：OpenAI API 期望 'assistant' 角色
                 messages.append({"role": "assistant", "content": entry["llm_response_raw"]})
            # 上一步动作执行的结果
            if "action_result" in entry:
                # 结果作为 'user' 角色反馈给模型通常不太合适， 
                # 更好的做法可能是将动作结果总结成文本放入下一步的 user prompt
                # 或者使用 function calling/tool use (更高级)
                # 为了简单起见，暂时还是模拟 LangChain 的方式，把结果作为 user 消息
                # 但标记一下，这可能不是最佳实践
                messages.append({"role": "user", "content": f"Action Result:\n```json\n{json.dumps(entry['action_result'], indent=2)}\n```"})

        # 最后加上当前状态和任务要求
        current_state_str = json.dumps(current_state, indent=2, ensure_ascii=False)
        prompt = f"Current Task: {task}\n\nCurrent Page State:\n```json\n{current_state_str}\n```\n\nBased on the current state (including the elements list) and history, determine the next action."
        # 当前的用户请求
        messages.append({"role": "user", "content": prompt})

        return messages

    # 这个方法现在不再是 async，因为我们的 AIClient.complete 是同步的
    # 如果 ai_client.complete 改为 async，这里也需要改回 async
    def get_next_action(self, task: str, current_state: Dict[str, Any], history: List[Dict[str, Any]]) -> Optional[LLMResponse]:
        """调用 AI Client 获取下一步动作建议。"""
        messages = self._construct_messages(task, current_state, history)

        logger.debug(f"准备调用 AI Client，发送 {len(messages)} 条消息。")

        response_text = ""
        response_data = {}
        try:
            # 调用我们自定义的 AI Client 的 complete 方法
            response_text = self.client.complete(
                messages=messages,
                model=self.default_model, # 可以传递，或者让 client 用自己的默认值
                temperature=self.default_temperature,
                max_tokens=self.default_max_tokens
            )
            logger.debug(f"AI Client 返回原始回复:\n{response_text}")

            # 清理掉可能的 Markdown 代码块标记 (比如 ```json ... ```)
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()
            elif response_text.strip().startswith("```"):
                 response_text = response_text.strip()[3:-3].strip()

            # 解析 JSON 字符串
            response_data = json.loads(response_text)
            # 用 Pydantic 模型验证一下结构对不对
            llm_response = LLMResponse.model_validate(response_data)
            return llm_response

        except AIClientError as e:
            # 捕获来自 AIClient 的特定错误
            logger.error(f"AI Client 调用失败: {e}")
            return LLMResponse(
                thought=f"出错了：调用 AI 服务失败: {e}",
                action=FinishAction(params=FinishParams(success=False, message=f"AI Client error: {e}"))
            )
        except json.JSONDecodeError as e:
            # 如果 JSON 解析失败 (这通常意味着 LLM 没有按要求返回 JSON)
            logger.error(f"解析 LLM 的 JSON 回复失败: {e}")
            logger.error(f"原始回复是:\n{response_text}")
            return LLMResponse(
                thought=f"出错了：没法把 LLM 的回复解析成 JSON。原始回复: {response_text}",
                action=FinishAction(params=FinishParams(success=False, message="LLM response parsing error."))
            )
        except ValidationError as e:
            # 如果 JSON 结构不对，通不过 Pydantic 验证
            logger.error(f"验证 LLM 回复结构失败: {e}")
            logger.error(f"返回的 JSON 数据是:\n{response_data}")
            return LLMResponse(
                thought=f"出错了：LLM 回复的格式不对。验证错误: {e}. 数据: {response_data}",
                action=FinishAction(params=FinishParams(success=False, message="LLM response validation error."))
            )
        except Exception as e:
            # 其他意想不到的错误
            logger.exception("处理 LLM 响应时发生未知错误:")
            return LLMResponse(
                thought=f"出错了：处理 LLM 响应时发生未知错误: {e}",
                action=FinishAction(params=FinishParams(success=False, message="Unexpected LLM handler error."))
            ) 