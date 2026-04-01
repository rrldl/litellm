import torch
import time

# 4GB 显存环境下，尝试占用约 2.4GB - 2.6GB
# 逻辑：float32 占用 4 bytes。
# 1024 * 1024 * 600 * 4 bytes ≈ 2400 MB (2.4GB)
print("EcoRoute 硬件压测启动...")
print("正在申请 2.4GB 显存占用...")

try:
    # 建立一个巨大的张量存放在 GPU 上
    device = torch.device("cuda:0")
    dummy_tensor = torch.randn(1024, 1024, 600, device=device)
    
    print("显存已成功占用！")
    print("当前显存状态：极高负载 (预计 > 60%)")
    
    while True:
        time.sleep(1)
except Exception as e:
    print(f" 运行失败: {e}")
except KeyboardInterrupt:
    print("\n释放显存，退出程序。")