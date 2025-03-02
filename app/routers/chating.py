from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import or_, and_, exists, func
from sqlalchemy.orm import Session, joinedload, aliased
from typing import List, Optional, Any
import json
import logging
from datetime import datetime
from app.util.generateJwt import create_jwt_token, verify_jwt_token
from app.database import get_db
from app.models import Friendship_model as models, User_model as userModels, Post_model as postModel, Chat_model as chatModel,Message_model as messageModel
from app.schema import chat_schema as schemas, api_response_schema as ApiSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chats"])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # Maps user_id to their WebSocket connection
        self.active_connections = {}
        # Maps (user_id, chat_id) to current draft content
        self.user_drafts = {}
        # Track active connections count
        self.connection_count = 0
    
    async def connect(self, websocket: WebSocket, user_id: str):
        try:
            await websocket.accept()
            self.active_connections[user_id] = websocket
            self.connection_count += 1
            logger.info(f"User {user_id} connected. Total connections: {self.connection_count}")
        except Exception as e:
            logger.error(f"Error connecting user {user_id}: {str(e)}")
            raise
    
    def disconnect(self, user_id: str):
        try:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
                self.connection_count -= 1
            
            # Remove all drafts from this user
            keys_to_remove = []
            for key in self.user_drafts.keys():
                uid, _ = key
                if uid == user_id:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.user_drafts[key]
                
            logger.info(f"User {user_id} disconnected. Remaining connections: {self.connection_count}")
        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {str(e)}")
    
    def update_draft(self, user_id: str, chat_id: int, draft_content: str):
        try:
            if draft_content:
                self.user_drafts[(user_id, chat_id)] = draft_content
            elif (user_id, chat_id) in self.user_drafts:
                del self.user_drafts[(user_id, chat_id)]
        except Exception as e:
            logger.error(f"Error updating draft for user {user_id}, chat {chat_id}: {str(e)}")
            raise
    
    def get_draft(self, user_id: str, chat_id: int) -> str:
        try:
            return self.user_drafts.get((user_id, chat_id), "")
        except Exception as e:
            logger.error(f"Error getting draft for user {user_id}, chat {chat_id}: {str(e)}")
            return ""
    
    def clear_draft(self, user_id: str, chat_id: int):
        try:
            if (user_id, chat_id) in self.user_drafts:
                del self.user_drafts[(user_id, chat_id)]
        except Exception as e:
            logger.error(f"Error clearing draft for user {user_id}, chat {chat_id}: {str(e)}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        try:
            if user_id in self.active_connections:
                await self.active_connections[user_id].send_json(message)
                logger.debug(f"Message sent to user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {str(e)}")
            return False
        
    async def check_online_status(self,user_id: str):
        try:
            if user_id in self.active_connections:
                logger.debug(f"the {user_id} is online")
                return True
            return False
        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {str(e)}")
            return False
    
    async def broadcast_to_chat(self, sender_id: str, chat_id: int, message: dict):
        """Send message to specific chat participant with isolation"""
        try:
            chat = message.get("chat")
            if not chat:
                logger.error(f"Chat object missing in message payload. Cannot determine recipient.")
                return False
                
            # Determine the correct recipient - strict one-to-one messaging
            recipient_id = chat.receiver_id if chat.sender_id == sender_id else chat.sender_id
            
            # Clean the message before sending (remove internal chat object)
            message_to_send = message.copy()
            if "chat" in message_to_send:
                del message_to_send["chat"]
            
            # Send to recipient if connected
            recipient_received = False
            if recipient_id in self.active_connections:
                await self.active_connections[recipient_id].send_json(message_to_send)
                recipient_received = True
                logger.debug(f"Message sent to recipient {recipient_id} in chat {chat_id}")
            
            # Also send back to sender to confirm delivery
            if sender_id in self.active_connections:
                await self.active_connections[sender_id].send_json(message_to_send)
                logger.debug(f"Confirmation sent to sender {sender_id}")
            
            return recipient_received    
        except Exception as e:
            logger.error(f"Error broadcasting to chat {chat_id}: {str(e)}")
            return False
    
    def get_connection_stats(self):
        """Get connection statistics for monitoring"""
        return {
            "active_connections": self.connection_count,
            "active_drafts": len(self.user_drafts)
        }

# Initialize connection manager
manager = ConnectionManager()

def get_chat_by_users(db: Session, user1_id: str, user2_id: str):
    try:
        # Check if chat exists with either user as sender or receiver
        chat = db.query(chatModel.Chat).filter(
            ((chatModel.Chat.sender_id == user1_id) & (chatModel.Chat.receiver_id == user2_id)) |
            ((chatModel.Chat.sender_id == user2_id) & (chatModel.Chat.receiver_id == user1_id))
        ).first()
        
        return chat
    except Exception as e:
        logger.error(f"Error getting chat between users {user1_id} and {user2_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/", response_model=ApiSchema.ApiResponse)
def create_chat(chat: schemas.ChatCreate, current_user_id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        # Verify users exist
        sender = db.query(userModels.User).filter(userModels.User.candidate_id == current_user_id).first()
        if not sender:
            raise HTTPException(status_code=404, detail="Current user not found")
        
        receiver = db.query(userModels.User).filter(userModels.User.candidate_id == chat.receiver_id).first()
        if not receiver:
            raise HTTPException(status_code=404, detail="Receiver not found")
        
        # Check if chat already exists
        existing_chat = get_chat_by_users(db, current_user_id, chat.receiver_id)
        logger.info(f"Checking existing chat between {current_user_id} and {chat.receiver_id}")
        if existing_chat:
            return ApiSchema.ApiResponse(
                status="success",
                status_code=201,
                message="Chat already exists",
                data={"chat_id": existing_chat.id}
            )
        
        # Create new chat
        db_chat = chatModel.Chat(
            sender_id=current_user_id,
            receiver_id=chat.receiver_id
        )
        db.add(db_chat)
        db.commit()
        db.refresh(db_chat)
        
        logger.info(f"New chat created between {current_user_id} and {chat.receiver_id}")
        
        return ApiSchema.ApiResponse(
            status="success",
            status_code=201,
            message="Chat created successfully",
            data={"chat_id": db_chat.id}
        )
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error creating chat: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create chat: {str(e)}")


@router.get("/all", response_model=ApiSchema.ApiResponse)
async def get_all_chats(current_user_id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        chats = db.query(chatModel.Chat).filter(
            (chatModel.Chat.sender_id == current_user_id) | (chatModel.Chat.receiver_id == current_user_id)
        ).all()

        if not chats:
            raise HTTPException(status_code=404, detail="No chats found")

        chat_data_list = []
        for chat in chats:
            other_user_id = chat.receiver_id if chat.sender_id == current_user_id else chat.sender_id
            other_user = db.query(userModels.User).filter(userModels.User.candidate_id == other_user_id).first()
            is_online = await manager.check_online_status(user_id=other_user_id)

            chat_data_list.append({
                "id": chat.id,
                "created_at": chat.created_at,
                "other_user": {
                    "id": other_user.candidate_id,
                    "username": other_user.user_name,
                    "profile_image": other_user.profile_image_url,
                    "is_online": is_online
                }
            })

        return ApiSchema.ApiResponse(
            status="success",
            status_code=200,
            message="Chats retrieved successfully",
            data=chat_data_list
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving chats for user {current_user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chats: {str(e)}")


@router.get("/{chat_id}", response_model=ApiSchema.ApiResponse)
async def get_chat(chat_id: int, current_user_id: str = Depends(verify_jwt_token), db: Session = Depends(get_db)):
    try:
        chat = db.query(chatModel.Chat).filter(chatModel.Chat.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Verify user is part of the chat
        if chat.sender_id != current_user_id and chat.receiver_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat")
        
        # Get other user info
        other_user_id = chat.receiver_id if chat.sender_id == current_user_id else chat.sender_id
        other_user = db.query(userModels.User).filter(userModels.User.candidate_id == other_user_id).first()
        
        chat_data = {
            "id": chat.id,
            "created_at": chat.created_at,
            "other_user": {
                "id": other_user.candidate_id,
                "username": other_user.user_name,
                "profile_image": other_user.profile_image_url
            }
        }
        
        return ApiSchema.ApiResponse(
            status="success",
            status_code=200,
            message="Chat retrieved successfully",
            data=[chat_data]
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error retrieving chat {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat: {str(e)}")
    
@router.get("/users/{user_id}/chats", response_model=ApiSchema.ApiResponse)
def get_user_chats(user_id: str, db: Session = Depends(get_db), current_user_id: str = Depends(verify_jwt_token)):
    try:
        # Verify the current user has permission to view these chats
        if current_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access other user's chats")
            
        # Get all chats where user is either sender or receiver
        chats = db.query(chatModel.Chat).filter(
            (chatModel.Chat.sender_id == user_id) | (chatModel.Chat.receiver_id == user_id)
        ).all()
        
        # Enhance chat data with other user info and last message
        enhanced_chats = []
        for chat in chats:
            # Get other user in the chat
            other_user_id = chat.receiver_id if chat.sender_id == user_id else chat.sender_id
            other_user = db.query(userModels.User).filter(userModels.User.candidate_id == other_user_id).first()
            
            # Get last message
            last_message = db.query(messageModel.Message)\
                .filter(messageModel.Message.chat_id == chat.id)\
                .order_by(messageModel.Message.created_at.desc())\
                .first()
                
            # Count unread messages
            unread_count = db.query(func.count(messageModel.Message.id))\
                .filter(
                    messageModel.Message.chat_id == chat.id,
                    messageModel.Message.sender_id != user_id,
                    messageModel.Message.is_read == False
                ).scalar()
                
            enhanced_chat = {
                "id": chat.id,
                "created_at": chat.created_at,
                "other_user": {
                    "id": other_user.candidate_id if other_user else None,
                    "username": other_user.username if other_user and hasattr(other_user, 'username') else "Unknown",
                    "profile_image": other_user.profile_image if other_user and hasattr(other_user, 'profile_image') else None
                },
                "last_message": {
                    "content": last_message.content if last_message else None,
                    "created_at": last_message.created_at if last_message else None,
                    "sender_id": last_message.sender_id if last_message else None
                } if last_message else None,
                "unread_count": unread_count
            }
            enhanced_chats.append(enhanced_chat)
        
        # Sort by last message time (most recent first)
        enhanced_chats.sort(
            key=lambda x: x["last_message"]["created_at"] if x["last_message"] else datetime.min,
            reverse=True
        )
        
        return ApiSchema.ApiResponse(
            status="success",
            message="User chats retrieved successfully",
            data=enhanced_chats
        )
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error retrieving chats for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chats: {str(e)}")


@router.get("/{chat_id}/messages", response_model=ApiSchema.ApiResponse)
async def get_chat_messages(
    chat_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        chat = db.query(chatModel.Chat).filter(chatModel.Chat.id == chat_id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Verify user is part of the chat
        if chat.sender_id != current_user_id and chat.receiver_id != current_user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat")
        
        # Get messages with pagination
        messages = (
            db.query(chatModel.Message)
            .filter(chatModel.Message.chat_id == chat_id)
            .order_by(chatModel.Message.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # Mark unread messages as read if current user is receiver
        try:
            unread_messages = []
            for message in messages:
                if message.sender_id != current_user_id and not message.is_read:
                    message.is_read = True
                    unread_messages.append(message.id)
            
            if unread_messages:
                db.commit()
                logger.info(f"Marked messages as read: {unread_messages}")
                
                # If the other user is connected, send read receipts
                other_user_id = chat.sender_id if chat.receiver_id == current_user_id else chat.receiver_id
                if other_user_id in manager.active_connections:
                    for msg_id in unread_messages:
                        read_receipt = {
                            "type": "read_receipt",
                            "message_id": msg_id,
                            "chat_id": chat_id,
                            "read_at": datetime.utcnow().isoformat()
                        }
                        await manager.send_personal_message(read_receipt, other_user_id)
                        
        except Exception as mark_err:
            logger.warning(f"Error marking messages as read: {str(mark_err)}")
            db.rollback()
            # Continue with the function despite this error
        
        # Enhance messages with sender info
        enhanced_messages = []
        for message in messages:
            sender = db.query(userModels.User).filter(userModels.User.candidate_id == message.sender_id).first()
            enhanced_message = {
                "id": message.id,
                "content": message.content,
                "sender_id": message.sender_id,
                "chat_id": message.chat_id,
                "created_at": message.created_at,
                "is_read": message.is_read,
                "sender": {
                    "username": sender.username if sender and hasattr(sender, 'username') else "Unknown",
                    "profile_image": sender.profile_image if sender and hasattr(sender, 'profile_image') else None
                } if sender else None
            }
            enhanced_messages.append(enhanced_message)
        
        # Return in chronological order
        return ApiSchema.ApiResponse(
            status="success",
            message="Messages retrieved successfully",
            data=list(reversed(enhanced_messages))
        )
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error retrieving messages for chat {chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve messages: {str(e)}")


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, db: Session = Depends(get_db)):
    try:
        user = db.query(userModels.User).filter(userModels.User.candidate_id == user_id).first()
        if not user:
            await websocket.close(code=4004, reason="User not found")
            return
        
        await manager.connect(websocket, user_id)
        
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message_data = json.loads(data)
                    message_type = message_data.get("type")
                    
                    if message_type == "draft_update":
                        try:
                            chat_id = message_data.get("chat_id")
                            draft_content = message_data.get("draft_content", "")
                            
                            # Verify chat exists and user is part of it
                            chat = db.query(chatModel.Chat).filter(chatModel.Chat.id == chat_id).first()
                            if not chat:
                                await manager.send_personal_message(
                                    {"type": "error", "message": "Chat not found"},
                                    user_id
                                )
                                continue
                            
                            # Strictly verify user is part of this chat
                            if chat.sender_id != user_id and chat.receiver_id != user_id:
                                await manager.send_personal_message(
                                    {"type": "error", "message": "Not authorized for this chat"},
                                    user_id
                                )
                                continue
                            
                            # Get the specific other user in this chat
                            other_user_id = chat.receiver_id if chat.sender_id == user_id else chat.sender_id
                            
                            # Update draft content
                            manager.update_draft(user_id, chat_id, draft_content)
                            
                            # Send draft update only to the specific recipient
                            draft_update = {
                                "type": "draft_update",
                                "chat_id": chat_id,
                                "user_id": user_id,
                                "draft_content": draft_content
                            }
                            
                            await manager.send_personal_message(draft_update, other_user_id)
                            
                        except Exception as draft_err:
                            logger.error(f"Error processing draft update: {str(draft_err)}")
                            await manager.send_personal_message(
                                {"type": "error", "message": "Error processing draft update"},
                                user_id
                            )
                    
                    elif message_type == "chat_message":
                        try:
                            chat_id = message_data.get("chat_id")
                            content = message_data.get("content")
                            
                            if not content or not chat_id:
                                continue
                            
                            # Verify chat exists and user is part of it
                            chat = db.query(chatModel.Chat).filter(chatModel.Chat.id == chat_id).first()
                            if not chat:
                                await manager.send_personal_message(
                                    {"type": "error", "message": "Chat not found"},
                                    user_id
                                )
                                continue
                            
                            # Strictly verify user is part of this chat
                            if chat.sender_id != user_id and chat.receiver_id != user_id:
                                await manager.send_personal_message(
                                    {"type": "error", "message": "Not authorized for this chat"},
                                    user_id
                                )
                                continue
                            
                            # Create and save message
                            db_message = messageModel.Message(
                                content=content,
                                sender_id=user_id,
                                chat_id=chat_id,
                                is_read=False
                            )
                            
                            try:
                                db.add(db_message)
                                db.commit()
                                db.refresh(db_message)
                            except Exception as db_err:
                                logger.error(f"Database error saving message: {str(db_err)}")
                                db.rollback()
                                await manager.send_personal_message(
                                    {"type": "error", "message": "Failed to save message"},
                                    user_id
                                )
                                continue
                            
                            # Clear draft for this user
                            manager.clear_draft(user_id, chat_id)
                            
                            # Get sender info for enhanced message
                            sender_info = {
                                "username": user.username if hasattr(user, 'username') else "Unknown",
                                "profile_image": user.profile_image if hasattr(user, 'profile_image') else None
                            }
                            
                            # Broadcast message to both users with improved isolation
                            message_response = {
                                "type": "chat_message",
                                "message_id": db_message.id,
                                "chat_id": chat_id,
                                "sender_id": user_id,
                                "content": content,
                                "created_at": db_message.created_at.isoformat(),
                                "is_read": False,
                                "sender": sender_info,
                                "chat": chat  # Include chat for proper recipient determination
                            }
                            
                            # Get the specific recipient
                            other_user_id = chat.receiver_id if chat.sender_id == user_id else chat.sender_id
                            
                            await manager.broadcast_to_chat(user_id, chat_id, message_response)
                            logger.info(f"Message sent from {user_id} to {other_user_id} in chat {chat_id}")
                            
                        except Exception as msg_err:
                            logger.error(f"Error processing chat message: {str(msg_err)}")
                            await manager.send_personal_message(
                                {"type": "error", "message": "Error processing message"},
                                user_id
                            )
                    
                    elif message_type == "read_receipt":
                        try:
                            message_id = message_data.get("message_id")
                            
                            if not message_id:
                                continue
                            
                            # Get the message
                            db_message = db.query(messageModel.Message).filter(messageModel.Message.id == message_id).first()
                            if not db_message:
                                await manager.send_personal_message(
                                    {"type": "error", "message": "Message not found"},
                                    user_id
                                )
                                continue
                            
                            # Get the chat
                            chat = db.query(chatModel.Chat).filter(chatModel.Chat.id == db_message.chat_id).first()
                            
                            # Verify user is part of the chat
                            if chat.sender_id != user_id and chat.receiver_id != user_id:
                                await manager.send_personal_message(
                                    {"type": "error", "message": "Not authorized for this chat"},
                                    user_id
                                )
                                continue
                            
                            # Only mark as read if current user is not the sender
                            if db_message.sender_id != user_id:
                                try:
                                    db_message.is_read = True
                                    db.commit()
                                except Exception as mark_err:
                                    logger.error(f"Error marking message as read: {str(mark_err)}")
                                    db.rollback()
                                    await manager.send_personal_message(
                                        {"type": "error", "message": "Failed to mark message as read"},
                                        user_id
                                    )
                                    continue
                                
                                # Notify sender that message was read
                                read_receipt = {
                                    "type": "read_receipt",
                                    "message_id": message_id,
                                    "chat_id": db_message.chat_id,
                                    "read_at": datetime.utcnow().isoformat()
                                }
                                
                                # Send only to the message sender
                                await manager.send_personal_message(read_receipt, db_message.sender_id)
                                logger.debug(f"Read receipt sent to {db_message.sender_id} for message {message_id}")
                        except Exception as receipt_err:
                            logger.error(f"Error processing read receipt: {str(receipt_err)}")
                            await manager.send_personal_message(
                                {"type": "error", "message": "Error processing read receipt"},
                                user_id
                            )
                    
                    elif message_type == "ping":
                        # Simple ping to keep connection alive
                        await manager.send_personal_message(
                            {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                            user_id
                        )
                        
                except json.JSONDecodeError as json_err:
                    logger.warning(f"Invalid JSON format from user {user_id}: {str(json_err)}")
                    await manager.send_personal_message(
                        {"type": "error", "message": "Invalid JSON format"},
                        user_id
                    )
                except Exception as process_err:
                    logger.error(f"Error processing message from user {user_id}: {str(process_err)}")
                    await manager.send_personal_message(
                        {"type": "error", "message": "Server error processing message"},
                        user_id
                    )
                    
        except WebSocketDisconnect:
            # Handle disconnection
            logger.info(f"WebSocket disconnected for user {user_id}")
            manager.disconnect(user_id)
        except Exception as ws_err:
            logger.error(f"WebSocket error for user {user_id}: {str(ws_err)}")
            manager.disconnect(user_id)
            
    except Exception as outer_err:
        logger.error(f"Outer error in WebSocket handler for user {user_id}: {str(outer_err)}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass


@router.get("/stats", response_model=ApiSchema.ApiResponse)
def get_connection_stats(current_user_id: str = Depends(verify_jwt_token)):
    """Get WebSocket connection statistics"""
    try:
        stats = manager.get_connection_stats()
        return ApiSchema.ApiResponse(
            status="success",
            message="Connection statistics retrieved",
            data=stats
        )
    except Exception as e:
        logger.error(f"Error getting connection stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve connection statistics")