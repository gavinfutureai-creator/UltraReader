"""
Q&A Prompt 模板

用于基于 Wiki 知识库回答问题
"""


class QAPrompts:
    """Q&A Prompt 模板"""

    SYSTEM = """你是一个基于知识库回答问题的助手。

你的职责：
1. 只基于提供的 Wiki 知识库内容回答问题
2. 引用具体的实体、关系、事件来支撑你的回答
3. 如果知识库中没有相关信息，明确告知用户
4. 用中文回答，保持回答的连贯性和可读性
5. 回答要具体，结合书中的具体情节和人物

禁止：
- 编造知识库中没有的信息
- 使用"根据知识库"等生硬的表达
- 回答与知识库内容矛盾的信息"""

    @classmethod
    def user(
        cls,
        book_title: str,
        wiki_content: str,
        question: str,
    ) -> str:
        """
        生成 Q&A 用户 Prompt

        Args:
            book_title: 书名
            wiki_content: Wiki 知识库内容
            question: 用户问题

        Returns:
            Q&A 用户 Prompt
        """
        return f"""## 书名: {book_title}

## 知识库内容:
{wiki_content}

## 问题:
{question}

## 你的任务

请基于上面的知识库内容回答问题。如果知识库中有相关信息，请结合具体的实体、关系、事件来回答。如果知识库中没有相关信息，请直接说明。

请用中文回答。"""
