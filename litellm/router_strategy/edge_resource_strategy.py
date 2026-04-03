import random
from typing import List, Optional, Union, Dict, Any
from litellm.router_strategy.base_routing_strategy import BaseRoutingStrategy

# 导入 EcoRoute 核心感知组件
from ..resource_monitor import monitor
from ..complexity_analyzer import analyzer

class EdgeResourceStrategy(BaseRoutingStrategy):
    """
    EcoRoute 核心决策类: 资源感知型边缘-云端协同调度策略
    学术亮点：
    1. 预判式硬约束 (Hard Constraint): 基于 KV-Cache 的显存预验机制。
    2. 多目标软优化 (Soft Optimization): 基于帕累托效率的效用函数。
    """
    
    def __init__(self, router, threshold: float = 85.0):
        self.router = router 
        # 为了展示 Task 4 的效果，我们把硬约束的阈值稍微调高一点，比如 85%
        self.threshold = threshold 
        print(f"\n[SYSTEM] EcoRoute 策略已启动 | 显存红线阈值: {self.threshold}%")
        print("★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★")
        print("[MULTI-OBJECTIVE] 基于效用函数的多目标优化决策引擎已激活！")
        print("★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★")

    def _calculate_utility(self, node_type: str, base_load_ratio: float, complexity_score: float, weights: Dict[str, float]) -> float:
        """
        数学建模：计算帕累托效用得分 (Utility Score)
        目标：分数越高 (越趋近 1.0)，代表越符合用户当前的偏好。
        """
        # 提取权重
        alpha_cost = weights.get("cost", 0.33)
        beta_latency = weights.get("latency", 0.33)
        gamma_quality = weights.get("quality", 0.33)

        if node_type == "edge":
            # 边缘节点：免费，但负载高时延迟大，且复杂任务质量差
            score_cost = 1.0
            score_latency = max(0.1, 1.0 - base_load_ratio) # 负载越高，得分越低
            score_quality = max(0.1, 1.0 - complexity_score) # 复杂度越高，边缘得分越低
        else:
            # 云端节点：收费，有网络延迟但算力稳定，质量始终最高
            score_cost = 0.2
            score_latency = 0.8
            score_quality = 1.0

        # 计算综合效用
        utility = (alpha_cost * score_cost) + (beta_latency * score_latency) + (gamma_quality * score_quality)
        return utility

    def get_available_deployment(self, 
                                 model_group: str, 
                                 healthy_deployments: List[Dict[str, Any]], 
                                 request_kwargs: Dict[str, Any], 
                                 messages: Optional[List[Dict[str, str]]] = None):
        
        # 1. 解析请求，提取用户偏好权重 (从 metadata 传入)
        metadata = request_kwargs.get("metadata", {}) or {}
        # 默认均衡模式：成本、延迟、质量各占 33%
        user_weights = metadata.get("preference_weights", {"cost": 0.33, "latency": 0.33, "quality": 0.33})
        pref_mode = metadata.get("preference_mode", "均衡模式 (Balanced)")

        # 2. 消息提取
        if messages is None:
            messages = (request_kwargs.get("messages") or request_kwargs.get("data", {}).get("messages") or [])
        user_content = messages[-1].get("content", "") if messages else ""

        # 3. 调用感知层 (Task 2 & 3)
        base_load_ratio = monitor.get_realtime_vram_usage()
        projected_load_ratio = monitor.get_system_load(request_content=user_content)
        delta_load_percent = (projected_load_ratio - base_load_ratio) * 100
        complexity_score = analyzer.get_complexity_score(messages)
        
        # 4. 节点拓扑识别
        edge_nodes, cloud_nodes = [], []
        for d in healthy_deployments:
            is_edge = "edge" in d.get("tags", [])
            if is_edge: edge_nodes.append(d)
            else: cloud_nodes.append(d)

        print(f"\n[EcoRoute 深度感知] 模式: {pref_mode}")
        print(f" ├─ 基础负载: {base_load_ratio*100:.1f}% | 任务预判峰值: {projected_load_ratio*100:.1f}% (+{delta_load_percent:.1f}%)")
        print(f" ├─ 语义复杂度: {complexity_score:.2f}")

        # ---------------------------------------------------------
        # 第一阶段：硬件红线保护 (Hard Constraint - Task 3)
        # ---------------------------------------------------------
        if projected_load_ratio * 100 > self.threshold:
            print(f">>> [EcoRoute 强制离载] 触发预判红线 ({projected_load_ratio*100:.1f}% > {self.threshold}%)，保护边缘节点，强制上云！")
            return cloud_nodes[0] if cloud_nodes else None

        # ---------------------------------------------------------
        # 第二阶段：多目标效用优化 (Soft Optimization - Task 4)
        # ---------------------------------------------------------
        # 计算两端效用分数
        u_edge = self._calculate_utility("edge", base_load_ratio, complexity_score, user_weights)
        u_cloud = self._calculate_utility("cloud", base_load_ratio, complexity_score, user_weights)

        print(f" ├─ 效用权重分布: [成本: {user_weights.get('cost')}, 时延: {user_weights.get('latency')}, 质量: {user_weights.get('quality')}]")
        print(f" ├─ 边缘效用得分 (U_edge): {u_edge:.3f}")
        print(f" └─ 云端效用得分 (U_cloud): {u_cloud:.3f}")

        # 根据帕累托最优进行决策
        if u_edge >= u_cloud and edge_nodes:
            print(f">>> [EcoRoute 决策] 路由至本地边缘 | 效用优胜 (U_edge: {u_edge:.2f} >= U_cloud: {u_cloud:.2f})")
            return edge_nodes[0]
        elif cloud_nodes:
            print(f">>> [EcoRoute 决策] 路由至云端集群 | 效用优胜 (U_cloud: {u_cloud:.2f} > U_edge: {u_edge:.2f})")
            return cloud_nodes[0]

        return healthy_deployments[0] if healthy_deployments else None