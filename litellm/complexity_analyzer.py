# litellm/complexity_analyzer.py

class ComplexityAnalyzer:
    def __init__(self):
        # 关键词库
        self.complex_keywords = [
            "code", "python", "java", "script", "c++", "cpp", "c#", "golang", "rust",
            "snippet", "leak", "debug", "refactor", "algorithm", "implementation",
            "pytorch", "cnn", "transformer", "math", "proof", "calculate", "summarize",
            "quicksort", "sort", "complex"
        ]

    def get_complexity_score(self, messages):
        if not messages:
            return 0.0
        
        content = ""
        try:
            # 1. 提取最后一条消息
            if isinstance(messages, list) and len(messages) > 0:
                last_msg = messages[-1]
            else:
                last_msg = messages

            # 2. 安全提取内容 (解决 Pylance 报错的关键)
            if isinstance(last_msg, dict):
                # 如果是字典，用 .get()
                content = last_msg.get("content", "")
            else:
                # 如果是对象，用 getattr 动态获取属性，避开静态类型检查
                # getattr(对象, "属性名", 默认值)
                content = getattr(last_msg, "content", "")
            
            # 3. 确保 content 是字符串（处理多模态或空值情况）
            if isinstance(content, list):
                # 某些模型 content 是列表 [{ "type": "text", "text": "..." }]
                content = " ".join([str(i) for i in content])
            
            content = str(content or "").lower()
            
            # 调试日志
            print(f" [Analyzer Debug] 提取内容: '{content[:50]}...'")

        except Exception as e:
            print(f" [Analyzer Error] 提取内容失败: {e}")
            return 0.05

        # --- 后续评分逻辑不变 ---
        score = 0.05
        hit_words = [w for w in self.complex_keywords if w in content]
        score += len(hit_words) * 0.3
        
        if len(content) > 30:
            score += 0.2
            
        final_score = min(score, 1.0)
        return final_score
    
analyzer = ComplexityAnalyzer()