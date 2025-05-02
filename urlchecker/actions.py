from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

# --- 定义各种动作需要啥参数 ---

class GoToURLParams(BaseModel):
    url: str = Field(..., description="要跳过去的网址。")

class ClickElementParams(BaseModel):
    selector: str = Field(..., description="要点的元素的 CSS 选择器。")
    # description: Optional[str] = Field(None, description="这个元素的描述（比如 '登录按钮'），给 LLM 看的，可选。")

class TypeTextParams(BaseModel):
    selector: str = Field(..., description="要在哪个输入框里打字，用 CSS 选择器指定。")
    text: str = Field(..., description="要输入的文字。")
    # description: Optional[str] = Field(None, description="输入框的描述（比如 '用户名输入框'），可选。")

class ExtractInfoParams(BaseModel):
    selectors: List[str] = Field(..., description="要从哪些元素里提取文字内容，用 CSS 选择器列表指定。")
    purpose: str = Field(..., description="说明一下要提取啥信息，为啥要提取。")

class FinishParams(BaseModel):
    success: bool = Field(..., description="任务是不是成功完成了。")
    message: str = Field(..., description="总结一下结果，或者把最后提取到的信息放这儿。")

# --- 定义每个单独的动作 ---

class GoToURLAction(BaseModel):
    action: Literal["goto_url"] = "goto_url"
    params: GoToURLParams

class ClickElementAction(BaseModel):
    action: Literal["click_element"] = "click_element"
    params: ClickElementParams

class TypeTextAction(BaseModel):
    action: Literal["type_text"] = "type_text"
    params: TypeTextParams

class ExtractInfoAction(BaseModel):
    action: Literal["extract_info"] = "extract_info"
    params: ExtractInfoParams

class FinishAction(BaseModel):
    action: Literal["finish"] = "finish"
    params: FinishParams

# --- 把所有动作类型合一起，方便 LLM 理解 ---

# 这个 Union 类型代表了 LLM 能选的所有动作
AgentAction = Union[
    GoToURLAction,
    ClickElementAction,
    TypeTextAction,
    ExtractInfoAction,
    FinishAction,
]

# --- 定义 LLM 输出的整体结构 ---

class LLMResponse(BaseModel):
    thought: str = Field(..., description="你是怎么想的，为啥选这个(些)动作，一步步说清楚。")
    # 如果以后想支持一步执行多个动作，可以打开下面这个，现在先一次一个
    action: AgentAction = Field(..., description="下一步要执行的那个动作。")
    # actions: List[AgentAction] = Field(..., description="接下来要按顺序执行的一系列动作。") 