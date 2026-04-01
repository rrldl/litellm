import psutil
import logging

# 1. 初始化变量为 None
pynvml = None
NVML_AVAILABLE = False

# 2. 尝试导入
try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    # 打印 debug 日志，而不是直接崩溃
    logging.debug("pynvml not found, GPU monitoring disabled.")

class ResourceMonitor:
    """边缘节点资源监控器"""
    def __init__(self):
        self.has_gpu = False
        # 3. 使用全局变量前先判断逻辑开关
        if NVML_AVAILABLE and pynvml is not None:
            try:
                pynvml.nvmlInit()
                self.has_gpu = True
            except Exception as e:
                logging.warning(f"NVML Init failed: {e}")
                self.has_gpu = False

    def get_vram_usage(self) -> float:
        """获取显存占用率"""
        if self.has_gpu and pynvml is not None:
            try:
                # 再次确认 pynvml 不为 None 且已初始化
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                return info.used / info.total
            except Exception:
                return 0.0
        return 0.0

    def get_system_load(self) -> float:
        """获取系统综合负载"""
        cpu_usage = psutil.cpu_percent(interval=None) / 100.0
        ram_usage = psutil.virtual_memory().percent / 100.0
        vram_usage = self.get_vram_usage()
        
        # 核心逻辑：取显存和内存中的最大压力值
        return max(vram_usage, ram_usage)

# 全局单例
monitor = ResourceMonitor()