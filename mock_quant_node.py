# mock_quant_node.py
import time
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.get("/health/vram")
def get_vram_status():
    # INT4 的显存占用极低，始终保持健康
    print("[INT4 量化副本] 收到网关探活！")
    return {"vram_load": 0.10, "status": "healthy"}

@app.post("/chat/completions")
async def fake_chat(request: Request):
    print("[INT4 量化副本]  激活降级执行！使用极低显存完成推理。")
    time.sleep(0.5) # 量化模型推理更快
    return {
        "id": "chatcmpl-quant",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "qwen-int4-edge",
        "choices":[{"index": 0, "message": {"role": "assistant", "content": "[降级执行/Graceful Degradation] 系统处于橙色预警状态。为您调度至 INT4 量化边缘模型，通过牺牲微小精度，保障系统不宕机。"}, "finish_reason": "stop"}]
    }

if __name__ == "__main__":
    print("=====================================================")
    print(" 本地边缘节点 (INT4 量化副本) 已启动！")
    print("监听 8003，专门用于 70%-85% 高压区间的弹性降级兜底...")
    print("=====================================================")
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="warning")