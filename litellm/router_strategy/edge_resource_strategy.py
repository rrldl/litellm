import random
from typing import List, Optional, Union, Dict, Any
from litellm.router_strategy.base_routing_strategy import BaseRoutingStrategy

# 导入 EcoRoute 核心感知组件
from ..resource_monitor import monitor
from ..complexity_analyzer import analyzer

class EdgeResourceStrategy(BaseRoutingStrategy):
    """
    EcoRoute 核心决策类: 资源感知型边缘-云端协同调度策略
    学术重点：基于负载预判(Proactive)与语义复杂度(Semantic)的双维度路由逻辑。
    """
    
    def __init__(self, router, threshold: float = 60.0):
        self.router = router 
        self.threshold = threshold
        # 预设复杂度阈值，建议为 0.5 (可根据实验动态调整)
        self.complexity_threshold = 0.5
        print(f"\n[SYSTEM] EcoRoute 策略已启动 | 负载阈值: {self.threshold}% | 复杂度阈值: {self.complexity_threshold}")
        print("★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★")
        print("[PROACTIVE] 基于 KV-Cache 预验的主动调度机制已激活！")
        print("★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★")

    def get_available_deployment(self, 
                                 model_group: str, 
                                 healthy_deployments: List[Dict[str, Any]], 
                                 request_kwargs: Dict[str, Any], 
                                 messages: Optional[List[Dict[str, str]]] = None):
        """
        核心路由决策算子：
        集成实时硬件监控与 KV-Cache 增量预判，实现“环境+任务”双维度确定性调度。
        """
        
        # 1. 鲁棒性消息提取
        if messages is None:
            messages = (
                request_kwargs.get("messages") or 
                request_kwargs.get("data", {}).get("messages") or
                request_kwargs.get("kwargs", {}).get("messages")
            )
        
        # 提取最新的用户 Prompt 用于计算预判增量
        user_content = ""
        if messages and isinstance(messages, list) and len(messages) > 0:
            user_content = messages[-1].get("content", "")

        # 2. 调用感知层：拆解负载指标
        # 获取当前纯硬件层面的真实负载 (Base Load)
        base_load_ratio = monitor.get_realtime_vram_usage()
        base_load_percent = base_load_ratio * 100
        
        # 获取加入任务后的预判峰值负载 (Projected Peak Load)
        projected_load_ratio = monitor.get_system_load(request_content=user_content)
        projected_load_percent = projected_load_ratio * 100 
        
        # 计算该任务带来的预期显存增量 (Delta Load)
        delta_load_percent = projected_load_percent - base_load_percent
        
        # 调用复杂度分析器 (Task 2 成果)
        complexity_score = analyzer.get_complexity_score(messages)
        
        # 3. 边缘/云端节点拓扑识别
        edge_nodes = []
        cloud_nodes = []
        
        for d in healthy_deployments:
            params = d.get("litellm_params", {})
            api_base = str(params.get("api_base", "")).lower()
            model_id = str(d.get("model_info", {}).get("id", "")).lower()
            tags = d.get("tags", [])
            
            is_edge = (
                "edge" in tags or 
                "127.0.0.1" in api_base or 
                "localhost" in api_base or 
                "local" in model_id
            )
            
            if is_edge:
                edge_nodes.append(d)
            else:
                cloud_nodes.append(d)

        # 4. 决策逻辑矩阵 (Academic Decision Matrix)
        should_offload = False
        reason = ""

        # A. 资源维度预判：如果预估峰值负载超过阈值 (60%)，强制离载
        if projected_load_percent > self.threshold:
            should_offload = True
            reason = f"预估显存峰值风险 ({projected_load_percent:.1f}%)"
            
        # B. 语义维度决策：如果任务复杂度超过阈值 (0.5)，为了精度离载
        elif complexity_score > self.complexity_threshold:
            should_offload = True
            reason = f"语义复杂度超限 ({complexity_score:.2f})"

        # 5. 格式化日志输出
        print(f"\n[EcoRoute 深度感知]")
        print(f" ├─ 实时硬件基础负载: {base_load_percent:.1f}%")
        print(f" ├─ 任务预期显存增量: {delta_load_percent:.1f}% (输入长度: {len(user_content)})")
        print(f" ├─ 最终模拟峰值负载: {projected_load_percent:.1f}%")
        print(f" └─ 语义维度复杂度评分: {complexity_score:.2f}")

        # 6. 执行路由决策
        if should_offload and cloud_nodes:
            target_node = cloud_nodes[0]
            print(f">>> [EcoRoute 决策]  离载至云端 | 原因: {reason}")
            return target_node
        
        if edge_nodes:
            print(f">>> [EcoRoute 决策]  本地推理 | 状态: 资源余量充足且任务在能力范围内")
            return edge_nodes[0]
        
        # Fallback: 如果没有识别出节点，返回第一个可用的
        return healthy_deployments[0] if healthy_deployments else None