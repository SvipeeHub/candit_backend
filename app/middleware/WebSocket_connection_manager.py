from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from typing import List, Dict, Optional, Set, Tuple

class ConnectionManager:
    def __init__(self):
        # Maps user_id to their WebSocket connection
        self.active_connections: Dict[int, WebSocket] = {}
        # Maps user_id to their current draft content per chat
        self.user_drafts: Dict[Tuple[str, int], str] = {}  # (user_id, chat_id) -> draft_content
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Remove all drafts from this user
        keys_to_remove = []
        for (uid, _) in self.user_drafts.keys():
            if uid == user_id:
                keys_to_remove.append((uid, _))
        
        for key in keys_to_remove:
            del self.user_drafts[key]
    
    def update_draft(self, user_id: str, chat_id: int, draft_content: str):
        self.user_drafts[(user_id, chat_id)] = draft_content
    
    def get_draft(self, user_id: str, chat_id: int) -> str:
        return self.user_drafts.get((user_id, chat_id), "")
    
    def clear_draft(self, user_id: str, chat_id: int):
        if (user_id, chat_id) in self.user_drafts:
            del self.user_drafts[(user_id, chat_id)]
    
    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
    
    async def broadcast_to_chat(self, sender_id: str, receiver_id: str, message: dict):
        # Send to receiver if connected
        if receiver_id in self.active_connections:
            await self.active_connections[receiver_id].send_json(message)
        
        # Also send back to sender to confirm delivery
        if sender_id in self.active_connections:
            await self.active_connections[sender_id].send_json(message)