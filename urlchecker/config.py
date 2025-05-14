"""
配置文件，包含AI模型配置
"""
import os
from dotenv import load_dotenv

load_dotenv() # 加载 .env 文件中的环境变量

AI_CONFIG = {
    # 指定要使用的AI源: 'OPENAI' (用于标准 OpenAI 或 Siliflow 等兼容 API)
    # 或未来可以添加 'CUSTOM_AI' 等
    "DEFAULT_AI_SOURCE": "OPENAI", 
    
    # OpenAI 或兼容 API 的配置 (根据 DEFAULT_AI_SOURCE 选择)
    "OPENAI": {
        # API Key: 优先从环境变量读取，其次用这里的默认值 (不推荐在代码中硬编码 Key)
        "API_KEY": os.getenv("OPENAI_API_KEY", "sk-24c8be486fe54cb29d13b79cf1555450"), 
        # API Base URL: 对于标准 OpenAI 通常不需要改，对于 Siliflow 或本地模型需要设置
        "API_BASE": os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1/"), 
        # 使用的模型名称 (例如 'gpt-3.5-turbo', 'gpt-4o', 或 Siliflow 上的模型名)
        "MODEL": os.getenv("OPENAI_MODEL", "qwen-max"), 
        # 模型温度 (0.0 表示更确定的输出)
        "TEMPERATURE": 0.0,
        # 生成内容的最大 Token 数量 (需要根据模型调整)
        "MAX_TOKENS": 1024 # 稍微调大一点，以容纳 JSON 输出和思考过程
    },
    
    # 示例: 如果未来要添加完全不同的自定义AI，可以像这样配置
    # "CUSTOM_AI": {
    #     "API_URL": "YOUR_CUSTOM_API_URL",
    #     "API_KEY": os.getenv("CUSTOM_AI_API_KEY", "YOUR_CUSTOM_KEY"),
    #     "MODEL": "custom-model",
    #     "IS_STREAMING": False,
    #     "TEMPERATURE": 0.1,
    #     "MAX_TOKENS": 500
    # }
}

# 可以在这里添加其他配置，比如浏览器设置等 (如果需要)
# BROWSER_CONFIG = {
#     "DEFAULT_HEADLESS": True
# } 