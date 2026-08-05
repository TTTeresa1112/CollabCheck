"""全局并发锁：防止搜索请求并发执行（含冷却时间）。"""
import threading
import time
import streamlit as st


class SearchLock:
    """Global lock to prevent concurrent searches with 30s freeze."""
    COOLDOWN_SECONDS = 5
    
    def __init__(self):
        self._lock = threading.Lock()
        self.last_search_finish_time = 0
    
    def get_status(self):
        """
        Returns unified status: (status_code, message)
        status_code: 'ready', 'busy', 'cooldown'
        """
        if self._lock.locked():
            return "busy", "系统正在处理其他请求，请稍候..."
        
        elapsed = time.time() - self.last_search_finish_time
        if elapsed < self.COOLDOWN_SECONDS:
            remaining = int(self.COOLDOWN_SECONDS - elapsed)
            return "cooldown", f"系统冷却中，请等待 {remaining} 秒后再试"
        
        return "ready", None

    def try_acquire(self):
        status, _ = self.get_status()
        if status != "ready":
            return False
        return self._lock.acquire(blocking=False)
    
    def release(self):
        if self._lock.locked():
            self._lock.release()
            self.last_search_finish_time = time.time()
    
    def force_unlock(self):
        if self._lock.locked():
            try:
                self._lock.release()
            except RuntimeError:
                pass


@st.cache_resource
def get_global_search_lock_v2():
    return SearchLock()


def get_search_lock_safe():
    """Safely get the search lock, handling Streamlit Cloud edge cases."""
    try:
        lock = get_global_search_lock_v2()
        # Verify it's actually a SearchLock instance with expected methods
        if hasattr(lock, 'get_status') and callable(lock.get_status):
            return lock
        else:
            # Invalid cached object, return a new instance
            st.cache_resource.clear()
            return get_global_search_lock_v2()
    except Exception:
        # Fallback: create a fresh instance
        return SearchLock()
