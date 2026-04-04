import random
from typing import List, Optional, Union, Dict, Any
from litellm.router_strategy.base_routing_strategy import BaseRoutingStrategy

from ..resource_monitor import monitor
from ..complexity_analyzer import analyzer
from ..peer_registry import registry 

class EdgeResourceStrategy(BaseRoutingStrategy):
    """
    EcoRoute 核心决策类: 端-边-云 (Device-Edge-Cloud) 三层协同调度
    Task 6 学术亮点：引入量化感知与优雅降级 (Graceful Degradation)。
    在 70%-85% 负载区间通过“精度-空间转换”实现系统韧性。
    """
    
    def __init__(self, router, threshold: float = 85.0):
        self.router = router 
        self.threshold = threshold # 危险红线：85% (引发 P2P 或上云)
        self.safe_zone = 70.0      # 安全线：70% (70-85 为橙色降级区)
        
        print(f"\n[SYSTEM] EcoRoute 策略已启动 | 预警线: {self.safe_zone}% | 危险红线: {self.threshold}%")
        print("★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★")
        print("[P2P CLUSTER & QUANT] 分布式协同与【动态量化降级】引擎已激活！")
        print("★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★")
        
        registry.start_sync()

    def _calculate_utility(self, node_type: str, node_load: float, complexity_score: float, weights: Dict[str, float]) -> float:
        """多目标效用函数计算 (帕累托寻优)"""
        alpha_cost = weights.get("cost", 0.33)
        beta_latency = weights.get("latency", 0.33)
        gamma_quality = weights.get("quality", 0.33)

        if node_type == "local_edge":
            score_cost = 1.0 
            score_latency = max(0.1, 1.0 - node_load) 
            score_quality = max(0.1, 1.0 - complexity_score)
        elif node_type == "local_quant": # Task 6 新增：INT4 节点
            score_cost = 1.0 
            score_latency = max(0.1, 1.0 - node_load) 
            # 【学术亮点：精度惩罚项 Accuracy Penalty】
            # 量化模型虽然省内存，但质量得分天然打 8.5 折 (-15%)
            score_quality = max(0.1, 1.0 - complexity_score) * 0.85
        elif node_type == "peer_edge":
            score_cost = 1.0 
            score_latency = max(0.1, 0.85 - node_load) # P2P 网络延迟惩罚
            score_quality = max(0.1, 1.0 - complexity_score)
        else: # cloud
            score_cost = 0.2
            score_latency = 0.8
            score_quality = 1.0

        return (alpha_cost * score_cost) + (beta_latency * score_latency) + (gamma_quality * score_quality)

    def get_available_deployment(self, model_group: str, healthy_deployments: List[Dict[str, Any]], request_kwargs: Dict[str, Any], messages: Optional[List[Dict[str, str]]] = None):
        metadata = request_kwargs.get("metadata", {}) or {}
        user_weights = metadata.get("preference_weights", {"cost": 0.8, "latency": 0.1, "quality": 0.1})
        pref_mode = metadata.get("preference_mode", "自适应弹性降级模式")

        if messages is None:
            messages = (request_kwargs.get("messages") or request_kwargs.get("data", {}).get("messages") or[])
        user_content = messages[-1].get("content", "") if messages else ""

        # 1. 提取本地物理负载
        local_base_load = monitor.get_realtime_vram_usage()
        projected_local_load = monitor.get_system_load(request_content=user_content)
        delta_load_percent = (projected_local_load - local_base_load) * 100
        complexity_score = analyzer.get_complexity_score(messages)
        
        edge_nodes, cloud_nodes = [],[]
        for d in healthy_deployments:
            tags = d.get("tags",[])
            api_base = d.get("litellm_params", {}).get("api_base", "")
            if "edge" in tags:
                edge_nodes.append(d)
                if "peer-edge" in tags and api_base:
                    registry.register_peer(api_base)
            else:
                cloud_nodes.append(d)

        print(f"\n[EcoRoute 弹性寻优] 模式: {pref_mode}")
        print(f" ├─ 本地 Node A 基础负载: {local_base_load*100:.1f}% | FP16 预期增量: +{delta_load_percent:.1f}%")
        print(f" ├─[边缘算力池 路由决策分析]")

        best_edge_node = None
        best_u_edge = -1.0
        
        for edge in edge_nodes:
            tags = edge.get("tags",[])
            api_base = edge.get("litellm_params", {}).get("api_base", "")
            is_quant = "quant-int4" in tags
            
            if "local-edge" in tags:
                node_type = "local_quant" if is_quant else "local_edge"
                node_name = "本地 Node A (INT4降级版)" if is_quant else "本地 Node A (FP16完整版)"
                node_load = local_base_load
                is_alive = True
            else:
                node_type = "peer_edge"
                node_name = f"协同 Node B (P2P:{api_base[-4:]})"
                peer_status = registry.get_peer_status(api_base)
                is_alive = peer_status["is_alive"]
                node_load = peer_status["vram_load"]

            if not is_alive:
                continue

            # Task 6：动态 VRAM 预算计算
            # 【核心逻辑】：量化模型对 KV-Cache 及激活内存的占用约减半！
            task_vram_impact = (delta_load_percent / 100)
            if is_quant:
                task_vram_impact *= 0.5 

            node_projected_load = node_load + task_vram_impact
            projected_pct = node_projected_load * 100

            # 绝对硬约束 (DANGER ZONE)
            if projected_pct > self.threshold:
                print(f" │   {node_name}: [红线拦截] 预算 {projected_pct:.1f}% > 85% -> 强制淘汰防 OOM")
                continue

            # 基础效用计算
            u = self._calculate_utility(node_type, node_load, complexity_score, user_weights)
            safety_penalty = 1.0

            # 动态量化感知 (QUANT ZONE: 70% ~ 85%)
            if "local-edge" in tags and projected_pct >= self.safe_zone:
                if not is_quant:
                    print(f" │   {node_name}: [橙色预警] 预算 {projected_pct:.1f}% -> 逼近崩溃边缘，施加重度拥塞惩罚 (-60%)")
                    safety_penalty = 0.4 # 拥塞惩罚，极大幅度压低 FP16 效用
                else:
                    print(f" │  {node_name}: [韧性激活] 预算 {projected_pct:.1f}% -> 精度换取空间，系统连续性得分为正")
            else:
                print(f" │   {node_name}: [健康] 预算 {projected_pct:.1f}%")

            u *= safety_penalty 
            print(f" │      └─ 最终效用得分 (U): {u:.3f}")
            
            if u > best_u_edge:
                best_u_edge = u
                best_edge_node = edge

        u_cloud = self._calculate_utility("cloud", local_base_load, complexity_score, user_weights)
        print(f" ├─ 云端大模型效用保底 (U_cloud): {u_cloud:.3f}")

        if best_edge_node and best_u_edge >= u_cloud:
            target_ip = best_edge_node.get('litellm_params', {}).get('api_base')
            print(f">>> [EcoRoute 决策] 路由至最优边缘节点: {target_ip} (U={best_u_edge:.2f})")
            return best_edge_node
        elif cloud_nodes:
            print(f">>> [EcoRoute 决策] 触发云端卸载 (U_cloud={u_cloud:.2f})")
            return cloud_nodes[0]

        return healthy_deployments[0] if healthy_deployments else None