import json
from typing import List
# 移除 AgentAction 的直接导入，因为我们不再单独生成它的成员 schema
# from mineAgent.actions import AgentAction 
# 增加导入
# from pydantic.json_schema import GenerateJsonSchema

# --- 手动定义的 LLMResponse JSON Schema ---
# 这个字符串需要精确反映 actions.py 中定义的模型结构
# 注意：JSON Schema 中通常不直接包含 descriptions，但可以添加
MANUAL_LLMRESPONSE_SCHEMA = {
    "title": "LLMResponse",
    "type": "object",
    "properties": {
        "thought": {
            "title": "Thought",
            "type": "string",
            "description": "你是怎么想的，为啥选这个(些)动作，一步步说清楚。" 
        },
        "action": {
            "title": "Action",
            "description": "下一步要执行的那个动作。",
            # 使用 anyOf 来表示 Union 类型 AgentAction
            "anyOf": [
                {
                    "title": "GoToURLAction",
                    "type": "object",
                    "properties": {
                        "action": {"const": "goto_url", "type": "string", "description": "动作名称"},
                        "params": {
                            "title": "GoToURLParams",
                            "type": "object",
                            "properties": {
                                "url": {"title": "Url", "type": "string", "description": "要跳过去的网址。"}
                            },
                            "required": ["url"]
                        }
                    },
                    "required": ["action", "params"]
                },
                {
                    "title": "ClickElementAction",
                    "type": "object",
                    "properties": {
                        "action": {"const": "click_element", "type": "string", "description": "动作名称"},
                        "params": {
                            "title": "ClickElementParams",
                            "type": "object",
                            "properties": {
                                "selector": {"title": "Selector", "type": "string", "description": "要点的元素的 CSS 选择器。"}
                            },
                            "required": ["selector"]
                        }
                    },
                    "required": ["action", "params"]
                },
                {
                    "title": "TypeTextAction",
                    "type": "object",
                    "properties": {
                        "action": {"const": "type_text", "type": "string", "description": "动作名称"},
                        "params": {
                            "title": "TypeTextParams",
                            "type": "object",
                            "properties": {
                                "selector": {"title": "Selector", "type": "string", "description": "要在哪个输入框里打字，用 CSS 选择器指定。"},
                                "text": {"title": "Text", "type": "string", "description": "要输入的文字。"}
                            },
                            "required": ["selector", "text"]
                        }
                    },
                    "required": ["action", "params"]
                },
                {
                    "title": "ExtractInfoAction",
                    "type": "object",
                    "properties": {
                        "action": {"const": "extract_info", "type": "string", "description": "动作名称"},
                        "params": {
                            "title": "ExtractInfoParams",
                            "type": "object",
                            "properties": {
                                "selectors": {
                                    "title": "Selectors", 
                                    "type": "array", 
                                    "items": {"type": "string"}, 
                                    "description": "要从哪些元素里提取文字内容，用 CSS 选择器列表指定。"
                                },
                                "purpose": {"title": "Purpose", "type": "string", "description": "说明一下要提取啥信息，为啥要提取。"}
                            },
                            "required": ["selectors", "purpose"]
                        }
                    },
                    "required": ["action", "params"]
                },
                {
                    "title": "FinishAction",
                    "type": "object",
                    "properties": {
                        "action": {"const": "finish", "type": "string", "description": "动作名称"},
                        "params": {
                            "title": "FinishParams",
                            "type": "object",
                            "properties": {
                                "success": {"title": "Success", "type": "boolean", "description": "任务是不是成功完成了。"},
                                "message": {"title": "Message", "type": "string", "description": "总结一下结果，或者把最后提取到的信息放这儿。"}
                            },
                            "required": ["success", "message"]
                        }
                    },
                    "required": ["action", "params"]
                }
            ]
        }
    },
    "required": ["thought", "action"]
}

# 获取 LLMResponse 模型对应的 JSON 结构
# 修改: 直接返回手动定义的 Schema 字符串
def get_response_format_json() -> str:
    # 不再需要导入 LLMResponse 或调用 model_json_schema
    # from mineAgent.actions import LLMResponse
    # schema = LLMResponse.model_json_schema(schema_generator=GenerateJsonSchema)
    # 直接返回手动构建的 Schema 的 JSON 字符串表示
    return json.dumps(MANUAL_LLMRESPONSE_SCHEMA, indent=2, ensure_ascii=False)

# 移除这个函数，因为它触发了错误
# def get_actions_schema_json() -> str:
#     from mineAgent.actions import AgentAction
#     action_schemas = [action_type.model_json_schema() for action_type in AgentAction.__args__]
#     return json.dumps(action_schemas, indent=2)

# 主要的系统提示模板 (修改)
SYSTEM_PROMPT_TEMPLATE = """
你是一个 AI 助手，任务是根据用户的指令来操作浏览器。
你的目标是浏览网页、和网页互动，最终完成用户的任务。

你会收到这些信息：
1. 用户指定的最终任务。
2. 浏览器当前页面的网址。
3. 当前页面的相关元素列表。
4. 你之前执行过的动作历史和结果（如果有的话）。

你需要决定下一步应该执行哪个动作，才能向完成任务目标更近一步。

响应格式：
你必须严格按照下面的 JSON 格式回复。这个格式包含了 'thought' 字段记录你的思考过程，以及 'action' 字段指定具体要执行的动作及其参数。请确保你的回复是一个合法的 JSON 对象，并且 'action' 字段的值符合下面 Schema 定义中列出的几种可能动作之一：
```json
{response_format}
```

指导原则：
- 仔细分析当前页面元素列表和整体任务。
- 一步步思考如何用可用的动作类型（如 'goto_url', 'click_element', 'type_text', 'extract_info', 'finish'）来完成任务，把思考过程写在 'thought' 字段里。
- 从可用动作中选择最合适的 *一个*，并根据上面提供的 Schema 格式，将其名称和参数正确地填入响应 JSON 的 'action' 字段中。
- 如果任务需要点击或输入文字，用 CSS 选择器来定位元素。选择器要尽量精确。
- 如果你觉得任务已经完成了，或者实在完成不了，就用 'finish' 动作。
- 'thought' 字段要简洁明了。
- 只输出 JSON 回复，前后不要加任何其他文字。
"""

def get_system_prompt() -> str:
    """生成最终的系统提示，把完整的响应格式 schema 塞进去。"""
    # actions_schema_str = get_actions_schema_json() # 移除
    response_format_str = get_response_format_json() # 获取手动定义的 schema 字符串
    return SYSTEM_PROMPT_TEMPLATE.format(
        # actions_schema=actions_schema_str, # 移除
        response_format=response_format_str
    ) 