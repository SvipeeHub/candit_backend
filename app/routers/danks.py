from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, and_, exists, func
from sqlalchemy.orm import Session, joinedload,aliased
from typing import List, Optional
from datetime import datetime
from app.util.generateJwt import create_jwt_token,verify_jwt_token
from app.database import get_db
from app.models import Danks_model as models,User_model as userModels,Post_model as postModel
from app.schema import friends_schema as schemas,api_response_schema as ApiSchema,dank_schema as DankSchmea

router = APIRouter(prefix="/danks", tags=["danks"])

@router.post("/danks/post", response_model=ApiSchema.ApiResponse)
async def send_post_dank(
    request: DankSchmea.PostDankCreate,
    current_user: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
      Seding Dank to the user 
      1. Send the post to the dank 
      2. Send the Anonymous Message 
    """
    try:
        # Verify receiver exists
        receiver = db.query(userModels.User).filter(
            userModels.User.candidate_id == request.receiver_id
        ).first()
        if not receiver:
            raise HTTPException(status_code=404, detail="Receiver not found")
        
        # Verify post exists
        if request.post_id:
            post = db.query(postModel.Post).filter(
            postModel.Post.post_id == request.post_id
            ).first()
            if not post:
                raise HTTPException(status_code=404, detail="Post not found")
        
        # Create new post dank
        new_dank = models.Dank(
            sender_id=current_user,
            receiver_id=request.receiver_id,
            post_id=request.post_id,
            message = request.message
        )
        
        db.add(new_dank)
        db.commit()
        db.refresh(new_dank)
        
        return {
           "status": "success",
           "message": "Dank Sent Successfully",
           "status_code": "201"
       }
       
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error sending post dank: {str(e)}")

@router.get("/received", response_model=ApiSchema.ApiResponse) 
async def get_received_danks(
    current_user: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        # Fetch danks received by the current user
        danks = db.query(models.Dank).filter(
            models.Dank.receiver_id == current_user
        ).all()
        
        # Prepare a list to store danks with their post details
        danks_with_posts = []
        
        # For each dank, fetch the associated post details
        for dank in danks:
            # Fetch the full post details associated with this dank
            post = db.query(postModel.Post).filter(
                postModel.Post.post_id == dank.post_id
            ).first() if dank.post_id else None
            
            # Create a dictionary that combines dank and post details
            dank_dict = {
                "dank_id": dank.dank_id,
                "sender_id": dank.sender_id,
                "receiver_id": dank.receiver_id,
                "post_id": dank.post_id,
                "message": dank.message,
                "is_read": dank.is_read,
                "send_at": dank.send_at,
                "expires_at": dank.expires_at,
                "post_details": post.__dict__ if post else None
            }
            
            # Remove SQLAlchemy internal key if present
            if dank_dict.get('post_details'):
                dank_dict['post_details'].pop('_sa_instance_state', None)
            
            danks_with_posts.append(dank_dict)
        
        return {
            "status": "success",
            "message": "Danks fetched successfully",
            "status_code": "200",
            "data": danks_with_posts
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching received danks: {str(e)}")
    

@router.post("/mark-read", response_model=ApiSchema.ApiResponse)
async def mark_dank_as_read(
    dank_id: str,
    current_user: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        # Find the specific dank
        dank = db.query(models.Dank).filter(
           models.Dank.dank_id == dank_id,
            models.Dank.receiver_id == current_user
        ).first()

        # Check if dank exists
        if not dank:
            raise HTTPException(
                status_code=404, 
                detail="Dank not found or you are not authorized to mark it as read"
            )

        # Mark as read
        dank.is_read = True
        db.commit()

        return {
            "status": "success",
            "message": "Dank marked as read successfully",
            "status_code": "200",
            "data": [{
                "dank_id": dank.dank_id,
                "is_read": dank.is_read
            }]
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400, 
            detail=f"Error marking dank as read: {str(e)}"
        )
