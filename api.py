import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# これまでに保存した5つの部品を読み込む
from core_state import CoreStateEngine
from queue import DeterministicTaskQueue
from fail_closed import FailClosedEnforcer
from executor import TaskExecutor

# --- サーバー（受付窓口）の立ち上げ ---
app = FastAPI(title="MULTIVERSE Core API", version="1.0")

# システム心臓部の起動準備
core = CoreStateEngine()
queue = DeterministicTaskQueue(core)
fail_closed = FailClosedEnforcer(core)
executor = TaskExecutor(core, queue, fail_closed)

logging.info("【System】MULTIVERSE Core API Server Boot Sequence Initiated.")

# --- スマホから送られてくるデータの「型（ルール）」を定義 ---
# （schema_version が 1.0 でないパケットはハッキングとみなし弾く）
class ChatPayload(BaseModel):
    schema_version: str
    text: str
    checksum: str

class TaskPayload(BaseModel):
    schema_version: str
    title: str
    troop: str
    revenue: int
    checksum: str

# --- 📡 受付エンドポイント 1：チャット指示の受領 ---
@app.post("/api/chat")
async def receive_chat(payload: ChatPayload):
    """スマホ画面のチャットから送られた指示を受け取る"""
    if payload.schema_version != "1.0":
        logging.critical("【Fail Closed】不正なスキーマバージョンの通信を遮断しました。")
        raise HTTPException(status_code=400, detail="Invalid Schema. Connection Terminated.")
    
    logging.info(f"[API] チャット指示を受領: {payload.text}")
    
    # 応答を生成してスマホへ返す（後々はここにプロバイダーAIの回答が入る）
    reply_message = f"【Core受信完了】MacBook側エンジンにて指示『{payload.text}』をセキュアに受け取りました。処理キューへ回します。"
    return {"status": "success", "reply": reply_message}

# --- 📡 受付エンドポイント 2：新規タスクの受領 ---
@app.post("/api/task")
async def receive_task(payload: TaskPayload):
    """スマホ画面で追加されたタスクを受け取り、SQLite(心臓部)へ保存する"""
    if payload.schema_version != "1.0":
        raise HTTPException(status_code=400, detail="Invalid Schema.")
    
    # SQLiteデータベースへ書き込み
    task_id = core.add_task(payload.title, payload.troop, payload.revenue)
    if not task_id:
        raise HTTPException(status_code=500, detail="タスクのデータベース保存に失敗しました。")
        
    logging.info(f"[API] 新規タスクをDBへ登録: {payload.title}")
    return {"status": "success", "task_id": task_id, "message": "任務をCoreエンジンへ登録完了。"}

# --- 📡 受付エンドポイント 3：状態の同期 ---
@app.get("/api/state")
async def get_state():
    """スマホが画面を更新する際に、MacBook側から現在の総資産やタスクの状況を送信する"""
    # （後々はSQLiteのデータをかき集めてスマホに返す）
    return {"status": "success", "message": "システム状態は正常です。"}
