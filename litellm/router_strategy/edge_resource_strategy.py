import psutil
import random
from typing import List, Optional, Union
from litellm.router_strategy.base_routing_strategy import BaseRoutingStrategy

class EdgeResourceStrategy(BaseRoutingStrategy):
    def __init__(self, router, threshold=60.0):
        # 1. 直接手动赋值，跳过 super() 的报错
        self.router = router 
        self.threshold = threshold
        
        # 2. 打印一条日志，证明初始化成功
        print(f" EdgeResourceStrategy Initialized with threshold: {self.threshold}%")

    def _get_system_load(self) -> float:
        """获取边缘侧负载：这里以系统内存为例，进阶可以改用显存"""
        # 面试重点：解释为什么选内存/显存作为调度指标
        return psutil.virtual_memory().percent

    def get_available_deployment(self, model_group, healthy_deployments, request_kwargs):
        current_load = self._get_system_load()
        
        # --- 更加鲁棒的节点识别逻辑 ---
        edge_nodes = []
        cloud_nodes = []

        for d in healthy_deployments:
            # 1. 获取该节点的参数
            params = d.get("litellm_params", {})
            api_base = str(params.get("api_base", "")).lower()
            model_id = str(d.get("model_info", {}).get("id", "")).lower()

            # 2. 逻辑判断：如果地址里有 127.0.0.1 或者 ID 里有 local，就判定为边缘节点
            if "127.0.0.1" in api_base or "localhost" in api_base or "local" in model_id:
                edge_nodes.append(d)
            else:
                cloud_nodes.append(d)

        # 打印一下，看看现在能不能抓到节点
        print(f"\n[Edge-Router] Load: {current_load}% | Found Edge: {len(edge_nodes)} | Found Cloud: {len(cloud_nodes)}")

        # --- 决策逻辑 ---
        if current_load < self.threshold and edge_nodes:
            print(f" -> Decision: [LOW LOAD] Using Local Model (ID: {edge_nodes[0].get('model_info', {}).get('id')[:8]}...)")
            return edge_nodes[0]
        elif cloud_nodes:
            print(f" -> Decision: [OFFLOAD] Using Aliyun Cloud.")
            return cloud_nodes[0]
        else:
            print(" -> Decision: [LAST RESORT] Random Fallback.")
            return healthy_deployments[0] if healthy_deployments else None