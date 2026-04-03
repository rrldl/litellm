
---

# EcoRoute-LLM: A Resource-Aware Edge-Cloud Collaborative Gateway
> **EcoRoute: 面向大语言模型的资源感知型端云协同智能网关**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.9%2B-green.svg)](https://www.python.org/)

## 1. 项目背景 (Motivation)
在边缘计算场景下，本地部署的轻量级大模型（LLM）面临双重挑战：
1. **显存瓶颈**：4GB 等小显存设备在处理长文本时极易发生 **OOM (Out-of-Memory)**。
2. **能力瓶颈**：小参数模型难以胜任高难度语义任务。

**EcoRoute-LLM** 通过深入 LiteLLM 路由层源码，构建了一个**预判式（Proactive）**与**多目标优化（Multi-Objective Optimization）**相结合的调度网关。它不仅能根据输入文本提前预算显存规避宕机，还能根据用户动态下发的偏好权重，计算帕累托最优的路由策略。

---

## 2. 系统架构 (System Architecture)

```mermaid
graph TD
    User([User Request with SLA Metadata]) --> Gateway{EcoRoute Gateway}
    Gateway -- "Phase 1: Hard Constraint (VRAM Budgeting)" --> Gateway
    Gateway -- "Phase 2: Soft Optimization (Utility Max)" --> Edge[Edge: Qwen-1.5B]
    Gateway -- "Phase 2: Soft Optimization (Utility Max)" --> Cloud[Cloud: Qwen-Plus]
    Edge --> Response
    Cloud --> Response
```

---

## 3. 核心技术实现 (Implementation Details)

本项目通过对 LiteLLM 源码的侵入式修改，实现了以下核心组件：

| 修改/新增文件 | 模块类型 | 核心贡献 (Key Contribution) |
| :--- | :--- | :--- |
| **`litellm/resource_monitor.py`** | 感知层 | **Task 3 核心**。集成 NVML 驱动，实现基于 KV-Cache 增量预判的显存预算算法。 |
| **`litellm/complexity_analyzer.py`** | 感知层 | **Task 2 核心**。构建关键词加权与意图特征提取引擎，评估 Prompt 语义难度。 |
| **`litellm/router_strategy/edge_resource_strategy.py`** | 决策层 | **Task 4 核心**。实现“硬约束拦截 + 多维效用函数软优化”的两阶段路由决策矩阵。 |
| **`litellm/router.py` (源码修改)** | 接入层 | 注册自定义路由策略，打通 Context 消息传递链路，解决异步上下文丢失 Bug。 |
| **`litellm/proxy/proxy_server.py` (修改)** | 系统层 | 修复 Windows 环境下 YAML 配置文件的 `gbk` 编码死锁问题，提升健壮性。 |


---

## 4. 阶段性开发任务详解 (Development Roadmap & Tasks)

本项目遵循“感知 $\rightarrow$ 决策 $\rightarrow$ 优化”的学术路径，共分为四个已完成阶段及两个规划阶段：

### 🏁 已完成任务 (Completed Tasks)

#### ✅ Task 1: 基础资源感知与水印离载 (Watermark-based Offloading)
*   **目标**：建立初步的边缘保护机制。
*   **实现**：集成 `psutil` 监控系统 CPU 与 RAM。通过设定 **60% 静态水印阈值**，当系统整体负载超标时，网关自动将请求重定向至云端，解决了边缘节点在高并发下的死机问题。

#### ✅ Task 2: 语义复杂度感知路由 (Semantic Complexity Awareness)
*   **目标**：解决边缘小模型“能力不足”导致的回答质量差问题。
*   **实现**：构建了一个**启发式语义分析引擎**。通过关键词权重匹配（如 `C++`, `Algorithm` 等高频逻辑词）结合文本长度特征，为每个 Prompt 计算复杂度评分（0-1.0）。实现“简单任务本地化，复杂任务云端化”。

#### ✅ Task 3: 显存预判式主动调度 (Proactive VRAM Budgeting) —— **[核心突破]**
*   **目标**：彻底解决 LLM 推理中最核心的 **OOM (显存溢出)** 风险。
*   **实现**：
    *   **底层接入**：废弃通用的 RAM 指标，通过 `pynvml` 直接读取 NVIDIA GPU 寄存器的实时显存。
    *   **预算模型**：引入 **KV-Cache 增量预估公式**。在推理开始前，根据输入的 Token 规模预计算即将产生的显存峰值。
    *   **主动防御**：实现“环境负载 + 任务增量”的双重判定，即使在受限环境下，也能通过预判精准避险。

#### ✅ Task 4: 基于效用函数的多目标优化调度 (Multi-Objective Optimization) —— **[系统化升级]**
*   **目标**：打破传统“一刀切”的规则调度，实现对用户个性化 SLA（服务等级协议）的支持。
*   **实现**：
    *   **数学建模**：提取端云协同中的“不可能三角”——**成本 (Cost)、时延 (Latency)、精度 (Quality)**，将其归一化并构建综合效用函数 (Utility Function)。
    *   **两阶段调度引擎**：将路由决策升级为两阶段：Phase 1 执行基于预判显存的**硬约束拦截 (Hard Constraint)** 以保护硬件；Phase 2 在安全区内执行**软优化 (Soft Optimization)**。
    *   **千人千面**：网关能够解析业务端动态下发的权重偏好（如“白嫖省钱模式”或“极致性能模式”），即使面对完全相同的 Prompt 任务，也能通过计算帕累托最优解，做出截然不同却最符合用户诉求的路由分配。

---

### 🚀 后期规划任务 (Future Roadmap)

#### 🌐 Task 5: 边缘 P2P 协同计算 (Edge-to-Edge Cluster Coordination)
*   **简介**：打破单设备瓶颈，构建**边缘算力池**。当本地节点 A 显存不足时，网关通过服务发现机制搜索局域网内的空闲节点 B。实现跨设备的负载均衡，最大化边缘侧的整体吞吐量。

#### ⚡ Task 6: 动态量化感知路由 (Adaptive Quantization Routing)
*   **简介**：实现更精细的“降级执行”。当负载处于临界区（如 70%-85%）时，网关不再简单上云，而是联动后端自动切换至更低比特（如 **INT4/NF4**）的量化模型。通过牺牲极小精度来换取系统的**连续可用性 (Service Continuity)**。

---


## 5. 运行效果展示 (Experimental Screenshots)

### 场景 1：基础任务本地执行 (Task 1 & 2 成果)
> 当负载低且复杂度低时，系统选择本地边缘侧以降低 Token 成本。
![场景1：简单对话留在本地](../images/simple_edge.png) 

### 场景 2：高难度任务语义离载 (Task 2 成果)
> 识别出代码生成等复杂逻辑，自动切换至云端大模型。
![场景2：复杂任务触发上云](../images/complex_cloud.png)

### 场景 3：长文本显存预算预判 (Task 3 核心成果)
> **亮点**：即使机器空闲，但因输入极长，算法预判到生成的 KV-Cache 将导致 OOM，提前拦截并上云。
![场景3：长文本预判上云](../images/long_text_proactive.png) 

### 场景 4：硬件负载饱和保护 (Task 3 核心成果)
> **亮点**：模拟后台任务挤占显存。即便任务极简，系统为保护硬件稳定性，强制执行云端离载。
![场景4：高压测自我保护](../images/hardware_stress_cloud.png)

### 场景 5：多目标帕累托优化 (Task 4 核心成果)
> **亮点**：相同的 Prompt，不同的用户偏好。当用户追求“省钱”时，系统留在本地；当用户追求“极致质量”时，系统上云。体现了工业级的动态 SLA 调度能力。
![场景5：多目标优化](../images/task4_multi_objective.png) 

---

## 6. 实验数据 (Experimental Results)

| 测试场景 | 硬件基础负载 | 任务预期增量 | 语义复杂度 | 路由决策 | 核心价值 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 基础问候 | 44.5% | 0.1% | 0.05 | **🏠 本地** | 节省 Token，快速响应 |
| 代码生成 | 44.5% | 0.5% | 0.55 | **🚀 云端** | 语义感知，质量保障 |
| 超长文本 | 47.0% | **53.0%** | 0.25 | **🚀 云端** | **预判避险，防止 OOM** |
| 极限压测 | **94.9%** | 3.4% | 0.05 | **🚀 云端** | **硬件红线保护** |
| **同Prompt: 省钱模式** | 45.1% | 3.6% | 0.85 | **🏠 本地** | **多目标：忍受高延迟换取零成本** |
| **同Prompt: 质量模式** | 45.9% | 3.6% | 0.85 | **🚀 云端** | **多目标：追求极速与高逻辑性** |

---

## 7. 快速开始 (Quick Start)

### 7.1 环境配置
```bash
git clone https://github.com/rrldl/litellm.git
pip install -e .
pip install psutil nvidia-ml-py torch requests
```

### 7.2 启动 EcoRoute 智能网关
```bash
# 启动网关端口 4000
python -m litellm.proxy.proxy_cli --config configs/test_config.yaml
```

### 7.3 验证多目标 SLA 调度 (Python)
```python
import requests, json

url = "http://127.0.0.1:4000/chat/completions"
prompt = "请解释一下什么是快速排序 (quicksort)，并给出一个基础的实现逻辑。"

# 模拟：省钱优先模式 (Economy)
payload = {
    "model": "my-qwen",
    "messages": [{"role": "user", "content": prompt}],
    "metadata": {
        "preference_mode": "省钱优先模式 (Economy)",
        "preference_weights": {"cost": 0.8, "latency": 0.1, "quality": 0.1}
    }
}
requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload))
```

---

## 8. 后续规划 (Roadmap)
Task 5: 边缘 P2P 协同计算 (Edge-to-Edge Cluster Coordination)

    简介：打破单设备瓶颈，构建边缘算力池。当本地节点 A 显存不足时，网关通过服务发现机制搜索局域网内的空闲节点 B。实现跨设备的负载均衡，最大化边缘侧的整体吞吐量。

⚡ Task 6: 动态量化感知路由 (Adaptive Quantization Routing)

    简介：实现更精细的“降级执行”。当负载处于临界区（如 70%-85%）时，网关不再简单上云，而是联动后端自动切换至更低比特（如 INT4/NF4）的量化模型。通过牺牲极小精度来换取系统的连续可用性 (Service Continuity)。

---

## 9. 致谢 (Acknowledgments)
感谢 **LiteLLM** 社区提供的模块化架构，使得自定义路由策略的实现成为可能。

---

