import psutil
import random
from typing import List, Optional, Union
from litellm.router_strategy.base_routing_strategy import BaseRoutingStrategy

class EdgeResourceStrategy(BaseRoutingStrategy):
    def __init__(self, router, threshold=80.0):
        super().__init__(router)
        self.threshold = threshold  # 资源水位线（百分比）

    def _get_system_load(self) -> float:
        """获取边缘侧负载：这里以系统内存为例，进阶可以改用显存"""
        # 面试重点：解释为什么选内存/显存作为调度指标
        return psutil.virtual_memory().percent

    def get_available_deployment(
        self,
        model_group: str,
        healthy_deployments: list,
        request_kwargs: dict
    ):
        """核心决策函数"""
        current_load = self._get_system_load()
        
        # 将模型分为本地(Edge)和云端(Cloud)
        edge_nodes = [d for d in healthy_deployments if "local" in d["model_info"].get("id", "").lower()]
        cloud_nodes = [d for d in healthy_deployments if "cloud" in d["model_info"].get("id", "").lower()]

        # 打印日志（方便你调试和展示）
        print(f"\n[Edge-Router] Current Load: {current_load}% | Threshold: {self.threshold}%")

        # 调度算法：基于阈值的溢出调度 (Threshold-based Offloading)
        if current_load < self.threshold and edge_nodes:
            print(" -> Decision: Low Load. Using Local Edge Model.")
            return random.choice(edge_nodes)
        elif cloud_nodes:
            print(" -> Decision: High Load/No Local Node. Offloading to Cloud.")
            return random.choice(cloud_nodes)
        else:
            return random.choice(healthy_deployments)