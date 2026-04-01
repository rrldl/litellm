import psutil
import logging
import os

# 尝试导入显卡驱动库
pynvml = None
NVML_AVAILABLE = False
try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    logging.debug("EcoRoute: pynvml 未安装，GPU 监控失效。")

class ResourceMonitor:
    """
    边缘节点资源感知器 (Proactive VRAM Budgeting Version)
    核心功能：通过实时显存监控与 KV-Cache 增量预验，实现预防式任务调度。
    """

    def __init__(self):
        # --- 模型架构先验参数 (以 Qwen-1.5B 为例) ---
        # 预估公式：Memory_KV_per_token = 2 * layers * num_heads * head_dim * precision_bytes
        # 对于 Qwen-1.5B (fp16): 2 * 28层 * 12头 * 128维度 * 2字节 / 1024^2 ≈ 0.082 MB/Token
        self.bytes_per_token_mb = 0.25 
        
        self.has_gpu = False
        self.gpu_count = 0
        self.handle = None

        # 1. 初始化驱动
        if NVML_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_count = pynvml.nvmlDeviceGetCount()
                if self.gpu_count > 0:
                    self.has_gpu = True
                    # 默认监控 0 号卡，也可扩展为多卡负载均衡
                    self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    print(f" EcoRoute [Task 3]: 已挂载 NVIDIA GPU 驱动，感知单元就绪。")
            except Exception as e:
                print(f"EcoRoute: GPU 驱动初始化失败 (环境可能无显卡): {e}")
                self.has_gpu = False

    def get_realtime_vram_usage(self) -> float:
        """获取当前硬件真实的实时显存占用率"""
        if not self.has_gpu: return psutil.virtual_memory().percent / 100.0
        try:
            info = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
            return info.used / info.total
        except: return 0.0

    def predict_peak_vram_load(self, prompt_text: str, max_new_tokens: int = 512) -> float:
        """
        预判式显存评估算法 (Proactive Estimation)
        原理：在 Decode 阶段，KV-Cache 会随 Token 序列线性增长。
        通过计算 (Prompt_len + Expected_len) * Unit_KV_Size 预估峰值，提前规避 OOM。
        """
        if not self.has_gpu:
            return 0.0
            
        try:
            info = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
            current_used_mb = info.used / (1024**2)
            total_mb = info.total / (1024**2)
            
            # 粗略计算 Token 数量 (按字符 1:1.5 估算，实际可用 tokenizer 进一步精确)
            estimated_prompt_tokens = len(prompt_text) / 2
            total_expected_tokens = estimated_prompt_tokens + max_new_tokens
            
            # 计算预估增量显存
            projected_kv_cache_mb = total_expected_tokens * self.bytes_per_token_mb
            
            # 加上 10% 的系统冗余缓冲区 (System Safety Buffer)
            peak_estimated_mb = current_used_mb + projected_kv_cache_mb * 1.1
            
            load_ratio = peak_estimated_mb / total_mb
            return min(load_ratio, 1.0) # 最高不超 100%
        except Exception:
            return self.get_realtime_vram_usage()

    def get_system_load(self, request_content: str = "") -> float:
        """
        负载感知的统一入口。
        如果提供了 request_content，则执行【预判式显存评估】；
        否则执行【实时显存监控】。
        """
        if self.has_gpu:
            if request_content:
                # 清洗乱码：只保留可打印字符
                request_content = "".join([c for c in request_content if c.isprintable() or c in [" ", "\n", "\t"]])
                #这里使用预判逻辑
                predicted_load = self.predict_peak_vram_load(request_content)
                print(f"[EcoRoute 预判] 输入长度: {len(request_content)} | 预估峰值负载: {predicted_load*100:.1f}%")
                return predicted_load
            else:
                # 常规心跳监控
                realtime_load = self.get_realtime_vram_usage()
                return realtime_load
        else:
            # CPU/RAM 环境回退方案
            ram_usage = psutil.virtual_memory().percent / 100.0
            return ram_usage

    def __del__(self):
        """释放 NVML 句柄"""
        if self.has_gpu:
            try:
                pynvml.nvmlShutdown()
            except:
                pass

# 全局单例
monitor = ResourceMonitor()