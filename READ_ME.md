# EcoRoute-LLM: Resource-Aware Edge-Cloud Collaborative Gateway
# (EcoRoute: 资源感知型端云协同大模型智能网关)

本项目旨在解决边缘侧设备（如 4GB 显存显卡）在部署大语言模型时面临的资源溢出（OOM）与性能波动问题。

## 核心进展 (Current Progress)
- [x] **任务一：基于水位线感知的端云离载 (RAM-based Offloading)**
  - 深入 LiteLLM 源码，注入自定义 `EdgeResourceStrategy` 路由策略。
  - 实现基于系统实时负载（Watermark）的动态分流逻辑：
    - 低负载 (<60%)：强制边缘侧 (GTX 1650 Ti) 推理，保障隐私与低时延。
    - 高负载 (>60%)：自动调度至云端 (Aliyun Qwen-Plus)，保障系统稳定性。
- [ ] **任务二：语义特征感知的任务分级 (Upcoming)**
- [ ] **任务三：基于 NVML 的显存级精准调度 (Upcoming)**

## 系统架构 (Architecture)
用户请求 -> LiteLLM 智能网关 (核心决策层) -> { 本地 Llama-cpp-python / 云端 Dashscope API }

## 快速开始 (Quick Start)
1. 启动本地服务器: `python local_server.py`
2. 启动智能网关: `python -m litellm.proxy.proxy_cli --config test_config.yaml`
3. 发送测试请求: `curl ...`