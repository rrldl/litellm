import random
from typing import List, Optional, Union
from litellm.router_strategy.base_routing_strategy import BaseRoutingStrategy

# 导入工具
from ..resource_monitor import monitor
from ..complexity_analyzer import analyzer

class EdgeResourceStrategy(BaseRoutingStrategy):
    def __init__(self, router, threshold=60.0):
        self.router = router 
        self.threshold = threshold
        print(f"EcoRoute 策略已启动 | 阈值: {self.threshold}%")

    def get_available_deployment(self, model_group, healthy_deployments, request_kwargs, messages=None):
        # 1. 抓取 messages
        if messages is None:
            messages = (
                request_kwargs.get("messages") or 
                request_kwargs.get("data", {}).get("messages") or
                request_kwargs.get("kwargs", {}).get("messages")
            )

        # 2. 获取实时状态
        current_load = monitor.get_system_load() * 100 
        complexity_score = analyzer.get_complexity_score(messages)
        
        # 3. 识别云/端节点
        edge_nodes = []
        cloud_nodes = []
        
        for d in healthy_deployments:
            params = d.get("litellm_params", {})
            api_base = str(params.get("api_base", "")).lower()
            model_id = str(d.get("model_info", {}).get("id", "")).lower()
            tags = d.get("tags", [])
            
            # 判断逻辑：有 edge 标签，或者地址是 127.0.0.1/localhost 的判定为边缘
            if "edge" in tags or "127.0.0.1" in api_base or "localhost" in api_base or "local" in model_id:
                edge_nodes.append(d)
            else:
                cloud_nodes.append(d)

        print(f"\n[EcoRoute-Status] CPU负载: {current_load:.1f}% | 任务复杂度: {complexity_score:.2f}")
        print(f"[EcoRoute-Nodes] 可用边缘: {len(edge_nodes)} | 可用云端: {len(cloud_nodes)}")

        # 4. 决策矩阵
        should_offload = False
        reason = ""

        if current_load > self.threshold:
            should_offload = True
            reason = "硬件负载过高"
        elif complexity_score > 0.5:
            should_offload = True
            reason = "任务过于复杂 (需云端大模型)"

        # 5. 执行分流
        if should_offload and cloud_nodes:
            print(f">>> [EcoRoute 决策] 🚀 离载至云端 | 原因: {reason}")
            return cloud_nodes[0]
        
        if edge_nodes:
            print(f">>> [EcoRoute 决策] 🏠 本地推理 | 目标: Edge Node")
            return edge_nodes[0]
        
        return healthy_deployments[0] if healthy_deployments else None