import random
from typing import List, Optional, Union, Dict, Any
from litellm.router_strategy.base_routing_strategy import BaseRoutingStrategy

from ..resource_monitor import monitor
from ..complexity_analyzer import analyzer
# 核心引入：Task 5 真实的 P2P 心跳探活中心
from ..peer_registry import registry 

class EdgeResourceStrategy(BaseRoutingStrategy):
    """
    EcoRoute 核心决策类: 端-边-云 (Device-Edge-Cloud) 三层协同调度
    学术亮点：不再使用随机数模拟！而是通过后台守护线程，读取真实的异步心跳软状态视图，实现 P2P 调度。
    """
    
    def __init__(self, router, threshold: float = 85.0):
        self.router = router 
        self.threshold = threshold 
        print(f"\n[SYSTEM] EcoRoute 策略已启动 | 显存红线阈值: {self.threshold}%")
        print("★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★")
        print("[P2P CLUSTER] 分布式边缘 P2P 算力寻优与真实心跳引擎已激活！")
        print("★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★")
        
        # 启动后台守护线程，开始向局域网节点发送心跳包
        registry.start_sync()

    def _calculate_utility(self, node_type: str, node_load: float, complexity_score: float, weights: Dict[str, float]) -> float:
        """多目标效用函数计算"""
        alpha_cost = weights.get("cost", 0.33)
        beta_latency = weights.get("latency", 0.33)
        gamma_quality = weights.get("quality", 0.33)

        if node_type == "local_edge":
            score_cost = 1.0 
            score_latency = max(0.1, 1.0 - node_load) # 本地无网络开销
            score_quality = max(0.1, 1.0 - complexity_score)
        elif node_type == "peer_edge":
            score_cost = 1.0 
            # 局域网有额外的网络时延惩罚 (减去 0.15)
            score_latency = max(0.1, 0.85 - node_load) 
            score_quality = max(0.1, 1.0 - complexity_score)
        else: # cloud
            score_cost = 0.2
            score_latency = 0.8
            score_quality = 1.0

        return (alpha_cost * score_cost) + (beta_latency * score_latency) + (gamma_quality * score_quality)

    def get_available_deployment(self, model_group: str, healthy_deployments: List[Dict[str, Any]], request_kwargs: Dict[str, Any], messages: Optional[List[Dict[str, str]]] = None):
        
        metadata = request_kwargs.get("metadata", {}) or {}
        user_weights = metadata.get("preference_weights", {"cost": 0.8, "latency": 0.1, "quality": 0.1})
        pref_mode = metadata.get("preference_mode", "局域网 P2P 协同模式")

        if messages is None:
            messages = (request_kwargs.get("messages") or request_kwargs.get("data", {}).get("messages") or[])
        user_content = messages[-1].get("content", "") if messages else ""

        # 1. 提取本地物理负载 (Node A)
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
                # 动态将配置文件里的 peer 节点注册到心跳中心
                if "peer-edge" in tags and api_base:
                    registry.register_peer(api_base)
            else:
                cloud_nodes.append(d)

        print(f"\n[EcoRoute 集群感知] 模式: {pref_mode}")
        print(f" ├─ 本地 Node A 基础负载: {local_base_load*100:.1f}% | 任务增量预判: +{delta_load_percent:.1f}%")
        print(f" ├─ 语义复杂度: {complexity_score:.2f}")
        print(f" ├─[边缘算力池 实时状态探查]")

        best_edge_node = None
        best_u_edge = -1.0
        
        # 2. 遍历算力池，基于【真实心跳数据】进行帕累托寻优
        for edge in edge_nodes:
            tags = edge.get("tags",[])
            api_base = edge.get("litellm_params", {}).get("api_base", "")
            
            if "local-edge" in tags:
                node_type = "local_edge"
                node_load = local_base_load
                node_name = "本地 Node A"
                is_alive = True
            else:
                node_type = "peer_edge"
                node_name = f"协同 Node B ({api_base})"
                # 【极其硬核】: 从内存表读取真实的异步心跳状态，彻底抛弃 Random 模拟！
                peer_status = registry.get_peer_status(api_base)
                is_alive = peer_status["is_alive"]
                node_load = peer_status["vram_load"]

            if not is_alive:
                print(f" │   ❌ {node_name} 状态: [宕机/失联] -> 绕过路由")
                continue

            # 硬约束拦截 (预判任务发过去会不会把对方搞崩溃)
            node_projected_load = node_load + (delta_load_percent / 100)
            if node_projected_load * 100 > self.threshold:
                print(f" │   ⚠️ {node_name} 状态: [高压预警] 当前负载 {node_load*100:.1f}%，加上任务将超限 -> 淘汰")
                continue

            # 计算软优化效用
            u = self._calculate_utility(node_type, node_load, complexity_score, user_weights)
            print(f" │   ✅ {node_name} 状态: [健康] 负载 {node_load*100:.1f}% | 效用得分: {u:.3f}")
            
            if u > best_u_edge:
                best_u_edge = u
                best_edge_node = edge

        # 3. 计算云端保底效用
        u_cloud = self._calculate_utility("cloud", local_base_load, complexity_score, user_weights)
        print(f" ├─ 云端集群效用得分 (U_cloud): {u_cloud:.3f}")

        # 4. 最终协同决策
        if best_edge_node and best_u_edge >= u_cloud:
            target_ip = best_edge_node.get('litellm_params', {}).get('api_base')
            print(f">>> [EcoRoute 协同调度] 🌐 路由至效用最优的边缘节点: {target_ip} (U={best_u_edge:.2f})")
            return best_edge_node
        elif cloud_nodes:
            print(f">>>[EcoRoute 越级调度] 🚀 边缘集群算力耗尽或云端效用更优，触发云端大模型 (U_cloud={u_cloud:.2f})")
            return cloud_nodes[0]

        return healthy_deployments[0] if healthy_deployments else None