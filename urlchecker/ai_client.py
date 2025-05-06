"""
AI 客户端模块，负责直接与 AI API 进行交互。
"""

import json
import requests
import logging
import sseclient # 虽然当前没用流式输出，但保持与 sql 示例结构一致
from typing import List, Dict, Any, Optional, Union, Callable, Generator

# 从新的 config.py 导入配置
from .config import AI_CONFIG

logger = logging.getLogger(__name__)

class AIClientError(Exception):
    """自定义 AI Client 异常"""
    pass

class AIClient:
    """AI 客户端基类"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
    
    def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        发送请求并获取完成结果。
        注意：现在接收的是 messages 列表，而不是单个 prompt 字符串。
        
        Args:
            messages: 发送给模型的聊天消息列表，格式如 [{'role': 'user', 'content': '...'}]
            **kwargs: 其他 API 参数，如 model, temperature, max_tokens
            
        Returns:
            AI 模型返回的核心内容字符串。
            
        Raises:
            AIClientError: 如果 API 请求失败或返回无效响应。
        """
        raise NotImplementedError("子类必须实现此方法")
    
    # 保留流式方法的定义，但暂时不实现或使用
    def stream_complete(self, messages: List[Dict[str, str]], callback: Callable[[str], None], **kwargs) -> None:
        raise NotImplementedError("流式处理在此版本中未实现")
    
    def generate_stream(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        raise NotImplementedError("流式处理在此版本中未实现")
        yield # 为了让它成为生成器

class OpenAIClient(AIClient):
    """OpenAI API (或兼容 API，如 Siliflow) 客户端"""
    
    def __init__(self, config_section: str = 'OPENAI'):
        """
        使用 config.py 中指定的部分初始化客户端。
        
        Args:
            config_section: AI_CONFIG 中要使用的配置块的名称 (例如 'OPENAI')
        """
        config = AI_CONFIG.get(config_section)
        if not config:
            raise ValueError(f"在 config.py 中未找到配置部分: {config_section}")
            
        super().__init__(config.get('API_KEY'))
        self.model = config.get('MODEL')
        self.api_base = config.get('API_BASE')
        self.temperature = config.get('TEMPERATURE', 0.0)
        self.max_tokens = config.get('MAX_TOKENS', 1024)
        
        if not self.api_key:
            logger.warning(f"配置部分 '{config_section}' 未找到 API_KEY，请确保你的 API 不需要 Key 或已在环境变量中设置。")
        if not self.model:
             raise ValueError(f"配置部分 '{config_section}' 缺少 MODEL 名称。")
        if not self.api_base:
            raise ValueError(f"配置部分 '{config_section}' 缺少 API_BASE URL。")

    def complete(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        使用 OpenAI 格式的 API 生成完成内容。
        """
        endpoint = f"{self.api_base.strip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}" 
        
        data = {
            "model": kwargs.get("model", self.model),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": False # 明确指定非流式
        }

        try:
            logger.debug(f"向 {endpoint} 发送请求，模型: {data['model']}, 消息数: {len(messages)}")
            response = requests.post(
                endpoint,
                headers=headers,
                json=data,
                timeout=180 # 设置超时，例如 3 分钟
            )
            
            response.raise_for_status() # 如果状态码不是 2xx，则抛出 HTTPError

            response_json = response.json()
            
            # 检查响应结构是否符合 OpenAI 格式预期
            if (
                not isinstance(response_json, dict)
                or "choices" not in response_json
                or not isinstance(response_json["choices"], list)
                or len(response_json["choices"]) == 0
                or not isinstance(response_json["choices"][0], dict)
                or "message" not in response_json["choices"][0]
                or not isinstance(response_json["choices"][0]["message"], dict)
                or "content" not in response_json["choices"][0]["message"]
            ):
                logger.error(f"API 响应格式无效: {response_json}")
                raise AIClientError("API 响应格式无效")

            content = response_json['choices'][0]['message']['content']
            logger.debug(f"从 API 成功获取内容，长度: {len(content)}")
            return content

        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败: {e}")
            raise AIClientError(f"API 请求失败: {e}") from e
        except json.JSONDecodeError as e:
             logger.error(f"解析 API 响应 JSON 失败: {e}")
             raise AIClientError("解析 API 响应 JSON 失败") from e # 移除错误的 from e
        except Exception as e:
            logger.exception("调用 API 时发生未知错误:") # 使用 exception 记录堆栈跟踪
            raise AIClientError(f"调用 API 时发生未知错误: {e}") from e

# 客户端获取函数 (类似 sql 项目)
def get_ai_client() -> AIClient:
    """
    根据 config.py 中的 DEFAULT_AI_SOURCE 获取 AI 客户端实例。
    """
    default_source = AI_CONFIG.get("DEFAULT_AI_SOURCE", "OPENAI").upper()
    
    if default_source == "OPENAI":
        # OpenAIClient 可以处理标准 OpenAI 和 Siliflow 等兼容 API
        # 它会读取 AI_CONFIG['OPENAI'] 下的配置
        logger.info("创建 OpenAI/兼容 API 客户端实例...")
        return OpenAIClient(config_section='OPENAI')
    # elif default_source == "CUSTOM_AI":
    #     # 如果未来添加 CustomAIClient，在这里实例化
    #     logger.info("创建自定义 AI 客户端实例...")
    #     # return CustomAIClient(config_section='CUSTOM_AI')
    else:
        raise ValueError(f"不支持的 AI 源在 config.py 中设置: {default_source}")

# 可以选择创建一个默认客户端实例供全局使用，如果方便的话
# default_ai_client = get_ai_client() 