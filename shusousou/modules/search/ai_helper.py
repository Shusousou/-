"""
书搜搜 - AI推荐模块
调用 DeepSeek API 生成图书推荐
"""

import json
import requests
from ...config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL


def get_recommendations(user_input: str) -> dict:
    """调用DeepSeek AI分析用户输入，生成推荐书单和搜索关键词
    
    Args:
        user_input: 用户的自然语言输入（如"我想看人工智能的书"）
        
    Returns:
        {
            "keywords": ["人工智能", "机器学习", ...],  # 用于查图书馆
            "books": [
                {
                    "title": "机器学习",
                    "author": "周志华",
                    "isbn": "978-7-302-45679-1",
                    "reason": "经典入门教材，适合初学者"
                },
                ...
            ]
        }
    """
    
    # 系统提示词
    system_prompt = """你是一个专业的图书推荐助手。请根据用户的输入，推荐相关的图书。

请按以下JSON格式返回结果（不要加任何额外的文字说明）：
{
    "keywords": ["关键词1", "关键词2", "关键词3"],
    "books": [
        {
            "title": "书名",
            "author": "作者",
            "isbn": "ISBN号",
            "reason": "推荐理由",
            "detail": "详细阅读建议"
        }
    ]
}

要求：
1. keywords 是用于图书馆搜索的关键词（3-5个），包含同义词/近义词
2. books 是推荐书单（3-5本），每本包含书名、作者、ISBN、推荐理由、详细阅读建议
3. ISBN要尽量真实
4. 推荐理由用一句话说明为什么推荐这本书（例如：适合什么水平的读者、书的亮点是什么）
5. 详细阅读建议写2-3句话，告诉用户：这本书适合什么基础的人看、需要先读什么、读的时候注意什么"""

    try:
        # 调用 DeepSeek API
        response = requests.post(
            url=DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            },
            timeout=15
        )
        
        # 解析返回结果
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # 提取JSON
        # 有时AI返回会包含markdown代码块 ```json ... ```
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("\n", 1)[0]
        if content.startswith("```json"):
            content = content[7:]
            content = content.rsplit("```", 1)[0]
        
        data = json.loads(content)
        return data
        
    except Exception as e:
        # API调用失败时返回模拟数据
        print(f"AI调用失败: {e}")
        return _mock_recommendation(user_input)


def _mock_recommendation(user_input: str) -> dict:
    """AI调用失败时的备用方案——返回模拟推荐数据"""
    
    # 根据关键词返回不同的模拟数据
    if "机器" in user_input or "人工智能" in user_input or "AI" in user_input or "ai" in user_input:
        return {
            "keywords": ["机器学习", "人工智能", "深度学习"],
            "books": [
                {"title": "机器学习", "author": "周志华", "isbn": "978-7-302-45679-1",
                 "reason": "国内最经典的机器学习入门教材，讲解透彻",
                 "detail": "适合有Python基础的初学者。建议先了解一些基本的概率统计知识再读。这本书偏理论，如果想动手实践可以配合《机器学习实战》一起看。"},
                {"title": "统计学习方法", "author": "李航", "isbn": "978-7-302-47752-9",
                 "reason": "理论扎实，适合想深入理解算法原理的读者",
                 "detail": "需要一定的数学基础（概率论、凸优化）。建议先读周志华的《机器学习》再读这本，效果更好。每章后的习题非常值得做。"},
                {"title": "深度学习", "author": "Ian Goodfellow", "isbn": "978-7-111-60888-8",
                 "reason": "深度学习领域的圣经级著作",
                 "detail": "适合已经掌握机器学习基础的读者。书很厚，建议先读前5章打基础，再根据自己的方向选择性阅读后面的章节。代码示例在GitHub上可以找到。"}
            ]
        }
    elif "科幻" in user_input or "三体" in user_input:
        return {
            "keywords": ["科幻", "三体"],
            "books": [
                {"title": "三体", "author": "刘慈欣", "isbn": "978-7-5366-9293-0",
                 "reason": "中国科幻巅峰之作，强烈推荐",
                 "detail": "适合所有读者，没有阅读门槛。建议先读完《三体》三部曲再看其他解读文章。如果喜欢硬科幻，这本书的物理想象力会让你惊艳。"},
                {"title": "流浪地球", "author": "刘慈欣", "isbn": "978-7-5404-8862-3",
                 "reason": "刘慈欣中短篇集，脑洞大开",
                 "detail": "适合喜欢短篇的读者，每篇独立可读。建议先看《流浪地球》同名电影再看原著，对比电影和原著的差异会很有趣。"}
            ]
        }
    elif "文学" in user_input or "小说" in user_input:
        return {
            "keywords": ["文学", "小说"],
            "books": [
                {"title": "活着", "author": "余华", "isbn": "978-7-5063-6782-8",
                 "reason": "余华代表作，看完让你思考人生",
                 "detail": "适合所有读者，语言通俗但情感深沉。建议一口气读完效果最好。读完后可以看看余华的《许三观卖血记》，风格类似。"},
                {"title": "红楼梦", "author": "曹雪芹", "isbn": "978-7-020-00220-7",
                 "reason": "中国古典文学巅峰，值得反复阅读",
                 "detail": "适合有一定耐心的读者。建议先看电视剧版（87版）建立兴趣，再读原著。前几回可能稍显枯燥，坚持到中段就会欲罢不能。"}
            ]
        }
    else:
        return {
            "keywords": [user_input],
            "books": [
                {"title": "Python编程：从入门到实践", "author": "Eric Matthes",
                 "isbn": "978-7-115-54608-1", "reason": "最适合编程初学者的入门书",
                 "detail": "适合完全没有编程基础的读者。建议边看书边动手敲代码，书中的项目练习一定要做。读完可以接着看《Python编程快速上手》。"},
                {"title": "算法导论", "author": "Thomas H. Cormen",
                 "isbn": "978-7-111-55701-8", "reason": "算法领域的经典教材",
                 "detail": "适合有编程基础的大学生阅读。建议先学一门编程语言再看。书很厚，不需要从头到尾读，可以按需选择章节。配合MIT的公开课效果更佳。"}
            ]
        }
