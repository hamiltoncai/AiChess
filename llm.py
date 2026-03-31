"""
LLM Integration for Chess Commentary
支持本地 Ollama 和 OpenCode API
"""
import requests
import json
from typing import Optional, Dict, Any

class LLMClient:
    """LLM客户端封装"""
    
    def __init__(self, backend: str = "none", base_url: str = None, model: str = None):
        """
        初始化LLM客户端
        Args:
            backend: "ollama" 或 "opencode" 或 "none"
            base_url: API基础URL
            model: 模型名称
        """
        self.backend = backend
        self.base_url = base_url
        self.model = model
        self.available = False
        
        # 默认配置
        if backend == "ollama":
            self.base_url = base_url or "http://localhost:11434"
            self.model = model or "llama3.2"
            self._check_ollama()
        elif backend == "opencode":
            self.base_url = base_url or "http://localhost:3000"
            self.model = model or "default"
            self._check_opencode()
        
        self.prompt_template = """你是一位专业的中国象棋和国际象棋评论员。请用简洁、有趣的语言评价这一步棋。

当前局面信息：
- 这步棋: {move_san}
- 棋步质量: {quality}
- 评估分数变化: {eval_change:+.0f} (厘兵值)
- 白方胜率变化: {prob_change:+.1f}%
- 当前白方胜率: {white_prob:.1f}%
- 黑方胜率: {black_prob:.1f}%
- 是否将军: {is_check}
- 是否吃子: {is_capture}

请用1-2句话评价这步棋，可以包含：
1. 战术分析
2. 棋理点评
3. 有趣的比喻或历史典故（可选）

回复语言：中文"""
    
    def _check_ollama(self) -> bool:
        """检查 Ollama 是否可用"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                print(f"✓ Ollama 可用，模型: {', '.join(model_names[:5])}")
                # 自动选择第一个可用模型
                if models and not self.model:
                    self.model = models[0].get("name", "llama3.2")
                self.available = True
                return True
        except Exception as e:
            print(f"✗ Ollama 不可用: {e}")
        self.available = False
        return False
    
    def _check_opencode(self) -> bool:
        """检查 OpenCode 是否可用"""
        try:
            # OpenCode 通常有健康检查端点
            response = requests.get(f"{self.base_url}/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ OpenCode API 可用")
                self.available = True
                return True
        except:
            pass
        
        # 尝试不同的端点
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=2)
            if response.status_code == 200:
                print(f"✓ OpenCode API 可用")
                self.available = True
                return True
        except Exception as e:
            print(f"✗ OpenCode 不可用: {e}")
        
        self.available = False
        return False
    
    def set_backend(self, backend: str, base_url: str = None, model: str = None):
        """切换后端"""
        self.backend = backend
        if base_url:
            self.base_url = base_url
        if model:
            self.model = model
        
        if backend == "ollama":
            self._check_ollama()
        elif backend == "opencode":
            self._check_opencode()
    
    def chat(self, message: str) -> str:
        """发送聊天请求"""
        if not self.available:
            return "LLM 服务暂不可用"
        
        if self.backend == "ollama":
            return self._chat_ollama(message)
        elif self.backend == "opencode":
            return self._chat_opencode(message)
        else:
            return ""
    
    def _chat_ollama(self, message: str) -> str:
        """使用 Ollama API"""
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": message}
                ],
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get("message", {}).get("content", "")
            else:
                return f"Ollama 错误: {response.status_code}"
        
        except Exception as e:
            return f"请求失败: {e}"
    
    def _chat_opencode(self, message: str) -> str:
        """使用 OpenCode API (OpenAI 兼容格式)"""
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": message}
                ]
            }
            
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                choices = response.json().get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
            return f"OpenCode 错误: {response.status_code}"
        
        except Exception as e:
            return f"请求失败: {e}"
    
    def analyze_move(self, move_analysis: Dict[str, Any], board_san: str = None) -> str:
        """
        分析棋步，生成评论
        Args:
            move_analysis: 来自 engine.get_move_analysis() 的分析结果
            board_san: 棋步的标准记号 (可选)
        Returns:
            LLM 生成的评论
        """
        if not self.available:
            # 返回基于规则的简单评论
            return self._rule_based_comment(move_analysis)
        
        prompt = self.prompt_template.format(
            move_san=move_analysis.get("move", "?"),
            quality=move_analysis.get("quality", "未知"),
            eval_change=move_analysis.get("eval_change", 0),
            prob_change=move_analysis.get("prob_change", 0),
            white_prob=move_analysis.get("white_win_prob_after", 50),
            black_prob=move_analysis.get("black_win_prob_after", 50),
            is_check="是" if move_analysis.get("is_check") else "否",
            is_capture="是" if move_analysis.get("is_capture") else "否"
        )
        
        return self.chat(prompt)
    
    def _rule_based_comment(self, analysis: Dict[str, Any]) -> str:
        """基于规则的简单评论（LLM 不可用时的后备方案）"""
        quality = analysis.get("quality", "正常")
        is_check = analysis.get("is_check", False)
        is_capture = analysis.get("is_capture", False)
        prob_after = analysis.get("white_win_prob_after", 50)
        
        comments = {
            "极好棋": "精彩！这是一步出色的棋。",
            "好棋": "好棋！这步棋走得不错。",
            "正常": "正常的一步棋。",
            "缓棋": "这步棋略显保守。",
            "不精确": "这步棋不够精确。",
            "失误": "失误！可能需要重新考虑。"
        }
        
        base_comment = comments.get(quality, "正常的一步棋。")
        
        # 添加将军或吃子的说明
        if analysis.get("is_checkmate"):
            return "将杀！游戏结束！"
        
        extras = []
        if is_check:
            extras.append("将军！")
        if is_capture:
            extras.append("吃子。")
        
        if prob_after > 70:
            extras.append("白方优势明显。")
        elif prob_after < 30:
            extras.append("黑方优势明显。")
        
        if extras:
            return base_comment + " " + " ".join(extras)
        return base_comment


# 全局 LLM 客户端实例
_llm_instance: Optional[LLMClient] = None

def get_llm(backend: str = "none", base_url: str = None, model: str = None) -> LLMClient:
    """获取全局 LLM 客户端实例"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient(backend, base_url, model)
    elif backend != "none":
        _llm_instance.set_backend(backend, base_url, model)
    return _llm_instance