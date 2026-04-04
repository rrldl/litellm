import threading
import time
import requests
import logging
from typing import Dict, Any

class PeerRegistry:
    """
    EcoRoute 边缘节点注册与状态同步中心 (Decentralized Service Discovery)
    学术价值：基于后台守护线程的异步 HTTP 心跳探活，维护边缘算力池的全局软状态视图。
    """
    
    def __init__(self, interval: int = 5):
        self.interval = interval
        # 核心数据结构：内存中的状态哈希表
        # 格式: { "http://192.168.1.100:8002": {"is_alive": True, "vram_load": 0.45, "last_seen": 169000...} }
        self.peers_state: Dict[str, Dict[str, Any]] = {}
        
        self._stop_event = threading.Event()
        # 声明为 Daemon 守护线程：主程序退出时，该线程会自动安全退出，不会造成僵尸进程
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread_started = False
        
        print(f"[P2P REGISTRY] 分布式边缘探活引擎已初始化 (心跳间隔: {self.interval}s)")

    def register_peer(self, peer_api_base: str):
        """将配置文件中解析出的局域网节点注册到状态表中"""
        # 规范化 URL，去掉末尾的 '/'
        peer_api_base = peer_api_base.rstrip('/')
        if peer_api_base not in self.peers_state:
            self.peers_state[peer_api_base] = {
                "is_alive": False, 
                "vram_load": 1.0, # 默认负载 100% (满载)，防止未知节点被分配任务
                "last_seen": 0
            }
            print(f"[P2P REGISTRY] 新增协同节点监控目标: {peer_api_base}")

    def start_sync(self):
        """启动后台心跳线程"""
        if not self._thread_started:
            self._thread.start()
            self._thread_started = True
            print("[P2P REGISTRY] 状态同步守护线程已启动...")

    def stop_sync(self):
        """优雅关闭线程"""
        self._stop_event.set()

    def _heartbeat_loop(self):
        """后台异步轮询机制 (核心逻辑)"""
        while not self._stop_event.is_set():
            for peer_url in list(self.peers_state.keys()):
                # 构造探活专用的轻量级 API (后续我们会写一个极简的脚本来响应这个 API)
                health_endpoint = f"{peer_url}/health/vram"
                try:
                    # 设置 1.5 秒超时，防止网络阻塞导致整个线程卡死
                    response = requests.get(health_endpoint, timeout=1.5)
                    if response.status_code == 200:
                        data = response.json()
                        self.peers_state[peer_url] = {
                            "is_alive": True,
                            "vram_load": data.get("vram_load", 1.0),
                            "last_seen": time.time()
                        }
                    else:
                        self._mark_dead(peer_url)
                except requests.exceptions.RequestException:
                    # 捕获所有网络异常 (连接拒绝、超时等)
                    self._mark_dead(peer_url)
            
            # 休眠等待下一次心跳周期
            time.sleep(self.interval)

    def _mark_dead(self, peer_url: str):
        """将无响应的节点标记为宕机"""
        if self.peers_state[peer_url]["is_alive"]:
            # 只有从 存活 -> 宕机 时才打印日志，避免刷屏
            logging.warning(f"[P2P REGISTRY] 协同节点失联: {peer_url}")
        self.peers_state[peer_url]["is_alive"] = False
        self.peers_state[peer_url]["vram_load"] = 1.0 # 宕机节点负载拉满，阻止路由

    def get_peer_status(self, peer_api_base: str) -> Dict[str, Any]:
        """供路由决策引擎 (Router Strategy) 调用的 $O(1)$ 读取接口"""
        peer_api_base = peer_api_base.rstrip('/')
        return self.peers_state.get(peer_api_base, {"is_alive": False, "vram_load": 1.0})

# 全局单例模式，保证网关内只有一份状态表
registry = PeerRegistry()