import asyncio
from playwright.async_api import async_playwright, Browser, Page, Playwright, ElementHandle
import logging
from typing import Dict, Any, Optional, List

from actions import (
    GoToURLAction,
    ClickElementAction,
    TypeTextAction,
    ExtractInfoAction,
    AgentAction
)

logger = logging.getLogger(__name__)

class BrowserController:
    def __init__(self, headless: bool = True):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.headless = headless # True 就是无头模式，不弹出浏览器窗口

    async def start(self):
        logger.info("启动浏览器控制器...")
        self.playwright = await async_playwright().start()
        # 用 Chromium，也可以换成 .firefox 或 .webkit
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        logger.info("浏览器启动成功。")

    async def close(self):
        logger.info("关闭浏览器控制器...")
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("浏览器已关闭。")

    async def _ensure_page(self):
        """确保 page 对象已经被初始化了"""
        if not self.page:
            raise Exception("浏览器页面还没初始化呢，先调用 start() 啊。")
        return self.page

    async def get_current_state(self) -> Dict[str, Any]:
        """获取浏览器当前页面的状态（URL、标题、关键元素列表）。"""
        page = await self._ensure_page()
        url = page.url
        title = await page.title()

        extracted_elements = []
        element_id_counter = 1
        MAX_ELEMENTS = 50 # 限制提取的元素总数

        # 定义我们关心的元素选择器
        # 交互式元素优先，然后是文本内容元素
        selectors = [
            'a', 
            'button', 
            'input:not([type="hidden"])', # 排除隐藏输入框
            'textarea', 
            'select',
            'h1', 'h2', 'h3', # 标题
            'p',             # 段落
            '[role="button"]', # ARIA role button
            '[role="link"]',   # ARIA role link
            '[role="textbox"]',# ARIA role textbox
            # 可以根据需要添加更多选择器，比如列表项 'li' 等
        ]

        try:
            for selector in selectors:
                if element_id_counter > MAX_ELEMENTS:
                    break # 达到元素数量上限

                # 找到所有匹配当前选择器的元素句柄
                elements: List[ElementHandle] = await page.locator(selector).element_handles()
                
                for element in elements:
                    if element_id_counter > MAX_ELEMENTS:
                        break 

                    # 只处理可见元素 (这是一个基本检查，可能不完美)
                    is_visible = await element.is_visible()
                    if not is_visible:
                        continue

                    element_info = {}
                    try:
                        tag_name = (await element.evaluate('el => el.tagName.toLowerCase()')).strip()
                        inner_text = (await element.inner_text()).strip().replace('\\n', ' ').replace('\\t', ' ')[:200] # 清理并限制长度
                        
                        # 获取一些常用属性
                        attributes = {}
                        common_attrs = ['aria-label', 'placeholder', 'name', 'type', 'value', 'href', 'alt', 'title', 'role']
                        for attr in common_attrs:
                            attr_value = await element.get_attribute(attr)
                            if attr_value is not None and attr_value.strip() != "":
                                attributes[attr] = attr_value.strip()

                        element_info = {
                            "id": element_id_counter, # 分配一个临时 ID
                            "tag": tag_name,
                            "text": inner_text if inner_text else None, # 如果没文本就设为 None
                            "attributes": attributes if attributes else None # 如果没属性就设为 None
                        }
                        
                        # 避免添加完全空的元素信息 (比如只有 ID 和 tag)
                        if element_info["text"] or element_info["attributes"]:
                            extracted_elements.append(element_info)
                            element_id_counter += 1
                        
                    except Exception as e_inner:
                        # 提取单个元素信息出错，跳过这个元素
                        logger.debug(f"提取元素信息失败 (ID 尝试分配 {element_id_counter}, Selector: {selector}): {e_inner}")
                        # 不需要增加 counter，因为这个元素没有成功添加
                        continue # 继续处理下一个元素
        
        except Exception as e_outer:
            logger.error(f"提取页面元素时发生错误: {e_outer}")
            # 即使出错，也返回基础信息
            return {
                "url": url,
                "title": title,
                "error_message": f"提取页面元素时出错: {str(e_outer)}",
                "elements": [], # 返回空列表
            }

        logger.info(f"提取了 {len(extracted_elements)} 个关键元素。")
        return {
            "url": url,
            "title": title,
            "elements": extracted_elements, # 用元素列表替换之前的简单 content
        }

    async def execute_action(self, action: AgentAction) -> Dict[str, Any]:
        """在浏览器页面上执行一个动作。"""
        page = await self._ensure_page()
        action_type = action.action
        params = action.params
        result = {"status": "success", "message": f"执行了 {action_type}"}

        logger.info(f"执行动作: {action_type}，参数: {params}")

        try:
            if action_type == "goto_url":
                # 增加超时时间到 60 秒 (单位是毫秒)
                await page.goto(params.url, wait_until="domcontentloaded", timeout=60000) 
                result["message"] = f"跳转到了 {params.url}"
            elif action_type == "click_element":
                # 也可以为点击等操作增加超时时间 (如果需要)
                await page.locator(params.selector).click(timeout=15000) # 例如 15 秒
                result["message"] = f"点击了元素，选择器: {params.selector}"
            elif action_type == "type_text":
                # 为输入操作增加超时
                await page.locator(params.selector).fill(params.text, timeout=15000) # 例如 15 秒
                result["message"] = f"在元素里输入了文字，选择器: {params.selector}"
            elif action_type == "extract_info":
                extracted_data = {}
                for selector in params.selectors:
                    try:
                        # 尝试获取文本内容；处理找不到元素或元素没文本的情况
                        element_texts = await page.locator(selector).all_text_contents()
                        # 如果找到多个匹配的元素，就把它们的文本用换行符合并，否则直接用第一个
                        extracted_data[selector] = "\n".join(element_texts) if element_texts else "没找到元素或者元素里没文字"
                    except Exception as e:
                        logger.warning(f"提取选择器 '{selector}' 的文本失败: {e}")
                        extracted_data[selector] = f"提取出错: {e}"
                result["message"] = f"为 '{params.purpose}' 提取了信息"
                result["extracted_data"] = extracted_data # 把提取到的数据也返回
            elif action_type == "finish":
                 result["message"] = f"收到 finish 动作: {params.message}"
            else:
                raise ValueError(f"不认识的动作类型: {action_type}")

            # 执行完动作稍微等一下... (这个 sleep 可能不再那么必要，因为操作本身有超时了)
            # await asyncio.sleep(1)

        except Exception as e:
            # 捕捉所有执行过程中可能出的错
            logger.error(f"执行动作 {action_type} 时出错: {e}")
            result["status"] = "error"
            result["message"] = f"执行 {action_type} 时出错: {str(e)}"

        return result 