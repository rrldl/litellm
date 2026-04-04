import random
from fastapi import FastAPI, Request
import uvicorn
import time

app = FastAPI()

@app.get("/health/vram")
def get_vram_status():
    mock_load = random.uniform(0.15, 0.25)
    print(f"[协同节点 Node B] 收到心跳探活！当前负载: {mock_load*100:.1f}%")
    return {"vram_load": mock_load, "status": "healthy"}

# --- 新增：接住网关转发过来的聊天请求 ---
@app.post("/chat/completions")
async def fake_chat(request: Request):
    print("[协同节点 Node B] 成功接手高负载任务！正在模拟边缘分布式推理...")
    # 模拟推理耗时
    time.sleep(1) 
    return {
        "id": "chatcmpl-mock",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "qwen-p2p-node-b",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "这是来自协同节点 Node B 的回复：检测到本地 Node A 负载过高，我已经成功接手并处理了您的长文本任务。"}, "finish_reason": "stop"}]
    }

if __name__ == "__main__":
    print("=====================================================")
    print("协同边缘节点 (Node B) 已启动！")
    print("监听 8002，已准备好接手转发任务...")
    print("=====================================================")
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="warning")