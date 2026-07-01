"""意图分类 prompt（不含 Persona，保持客观判断）"""
from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    intent: str = Field(description="意图类型: score_query / academic_advice / knowledge_qa / data_query / weather_query / image_generation / commute_plan / nearby_service / email_draft / supervisor_multi_agent / emotional_support / general_chat")
    confidence: float = Field(description="置信度 0.0-1.0")


INTENT_CLASSIFY_PROMPT = """你是一个意图分类器。分析用户消息，判断意图类型。

意图类型说明：
- score_query：查询成绩、问分数、问某科表现。例如"帮我查成绩""我数学怎么样""这次考试多少分"
- academic_advice：请求学业分析、学习建议、成绩趋势解读。例如"我最近成绩有进步吗""怎么提高数学成绩""帮我分析这学期表现"
- knowledge_qa：询问学校制度、系统使用方法、名著/文学知识。例如"请假流程是什么""怎么查成绩""桃园三结义是哪三人"
- data_query：开放式数据库查询，无法用固定成绩/学生工具解决。例如"3班有多少人""哪些学生成绩超过90分"
- weather_query：查询天气相关信息。例如"今天天气怎么样""北京明天会下雨吗""深圳空气质量如何"
- image_generation：请求生成图片、海报、插画、封面等视觉内容。例如"帮我生成一张海报""画一只奔跑的柯基""生成校园活动插画"
- commute_plan：规划通勤或出行路线。例如"从学校到腾讯滨海大厦坐地铁怎么去""从宿舍到实习公司开车要多久"
- nearby_service：查询某地点附近/周边的生活服务或 POI。例如"腾讯滨海大厦附近有什么吃饭的地方""宝安附近有没有医院""广州天河周边有打印店吗"
- email_draft：写邮件、发邮件、生成邮件内容。例如"帮我写封请假邮件""给老师发一封感谢信""帮我回复一下那封邮件"
- supervisor_multi_agent：明确需要多个领域协作，例如先规划路线再写邮件通知、先查周边地点再生成沟通内容。当前由后端 Supervisor 确定性接管，分类器只作识别兜底
- emotional_support：表达压力、焦虑、烦恼等情绪。例如"我压力好大""考试好紧张""最近很烦"
- general_chat：日常闲聊、打招呼、与系统业务无关的对话。例如"你好""今天天气不错""你是谁"

分类规则：
1. 如果用户明确提到"成绩""分数""考试"且是查询语气 → score_query
2. 如果用户请求"分析""建议""趋势""怎么办（学习相关）" → academic_advice
3. 如果用户询问制度、规则、系统操作、文学知识 → knowledge_qa
4. 如果用户问数据统计类问题（多少人、哪些人、排名等） → data_query
5. 如果用户问天气、温度、下雨、空气质量等气象相关 → weather_query
6. 如果用户请求生成图片、插画、海报、封面、配图等视觉内容 → image_generation
7. 如果用户询问从某地到某地的通勤、路线、公交、地铁、开车、步行方案 → commute_plan
8. 如果用户询问某地点附近/周边/旁边有什么服务、店铺、医院、餐饮、打印店、银行、地铁站等 → nearby_service
9. 如果用户请求写邮件、发邮件、回复邮件 → email_draft
10. 如果用户在同一句里明确要求地图任务和邮件任务协作 → supervisor_multi_agent
11. 如果用户表达情绪、压力、烦恼且不带明确查询需求 → emotional_support
12. 以上都不匹配 → general_chat

请根据用户消息输出意图分类结果。"""
