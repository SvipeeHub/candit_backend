from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, and_, exists, func
from sqlalchemy.orm import Session, joinedload,aliased
from typing import List, Optional
from datetime import datetime
from app.util.generateJwt import create_jwt_token,verify_jwt_token
from app.database import get_db
from app.models import Friendship_model as models,User_model as userModels,Post_model as postModel
from app.schema import friends_schema as schemas,api_response_schema as ApiSchema

router = APIRouter(prefix="/friends", tags=["friends"])

@router.post("/request/{friend_id}")
async def send_friend_request(
    friend_id: str,
    current_user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        if friend_id == current_user_id:
            raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")

        # Check if friendship already exists
        existing_friendship = db.query(models.Friendship).filter(
            or_(
                and_(
                    models.Friendship.user_id == current_user_id,
                    models.Friendship.friend_id == friend_id
                ),
                and_(
                    models.Friendship.user_id == friend_id,
                    models.Friendship.friend_id == current_user_id
                )
            )
        ).first()

        if existing_friendship:
            raise HTTPException(status_code=400, detail="Friendship already exists")

        # Create new friendship request
        friendship = models.Friendship(
            user_id=current_user_id,
            friend_id=friend_id,
            action_user_id=current_user_id,
            status='PENDING'  # Using string directly instead of enum
        )
        
        db.add(friendship)
        db.commit()
        
        return {"message": "Friend request sent successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/", response_model=ApiSchema.ApiResponse)
async def get_friends(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,  # Changed from enum to string
    current_user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        # Base query
        query = (
            db.query(userModels.User)
            .join(
                models.Friendship,
                or_(
                    and_(
                        models.Friendship.user_id == current_user_id,
                        models.Friendship.friend_id == userModels.User.candidate_id
                    ),
                    and_(
                        models.Friendship.friend_id == current_user_id,
                        models.Friendship.user_id == userModels.User.candidate_id
                    )
                )
            )
            .options(joinedload(userModels.User.friend_of))
        )

        # Apply filters
        if status:
            query = query.filter(models.Friendship.status == status)
        else:
            query = query.filter(models.Friendship.status ==status)  # Using string instead of enum

        if search:
            query = query.filter(userModels.User.user_name.ilike(f"%{search}%"))

        total = query.count()

        friends = (
            query
            .order_by(userModels.User.user_name)
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
     
        items= [
                {
                    "id": friend.id,
                    "user_id":friend.candidate_id,
                    "username": friend.user_name,
                    "profile_image_url": friend.profile_image_url if friend.profile_image_url else None,
                    "anonymous_id":friend.anonymous_id,
                    "firstName":friend.first_name,
                    "lastName":friend.last_name,
                    "is_active":friend.is_active
                }
                for friend in friends
            ]
            
           

        return {
             "status": "success",
             "status_code": "200",
             "data":items,
             "total": total,
             "page": page,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/requests/{friendship_id}/accept")
async def accept_friend_request(
    friendship_id: str,
    current_user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        friendship = db.query(models.Friendship).filter(
            models.Friendship.friend_id == current_user_id,
            models.Friendship.user_id == friendship_id,
            models.Friendship.status == 'PENDING'  # Using string instead of enum
        ).first()

        if not friendship:
            raise HTTPException(status_code=404, detail="Friend request not found")

        friendship.status = 'ACCEPTED'  # Using string instead of enum
        friendship.action_user_id = current_user_id
        friendship.updated_at = datetime.utcnow()
        
        db.commit()

        return {"message": "Friend request accepted"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{friend_id}")
async def remove_friend(
    friend_id: str,
    current_user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        friendship = db.query(models.Friendship).filter(
            or_(
                and_(
                    models.Friendship.user_id == current_user_id,
                    models.Friendship.friend_id == friend_id
                ),
                and_(
                    models.Friendship.user_id == friend_id,
                    models.Friendship.friend_id == current_user_id
                )
            )
        ).first()

        if not friendship:
            raise HTTPException(status_code=404, detail="Friendship not found")

        db.delete(friendship)
        db.commit()

        return {"message": "Friend removed successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/suggestions", response_model=ApiSchema.ApiResponse)
async def get_friend_suggestions(
    limit: int = Query(20, ge=1, le=100),
    current_user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        # Create a subquery to get all users involved in friendships
        friendship_users = (
            db.query(models.Friendship)
            .filter(
                or_(
                    models.Friendship.user_id == current_user_id,
                    models.Friendship.friend_id == current_user_id
                )
            )
        )

        # Get users who are not in any friendship relation with current user
        suggestions = (
            db.query(userModels.User)
            .filter(userModels.User.candidate_id != current_user_id)
            .filter(
                ~exists().where(
                    or_(
                        models.Friendship.user_id == userModels.User.candidate_id,
                        models.Friendship.friend_id == userModels.User.candidate_id,
                    )
                    & or_(
                        models.Friendship.user_id == current_user_id,
                        models.Friendship.friend_id == current_user_id
                    )
                )
            )
            .order_by(func.random())
            .limit(limit)
            .all()
        )

        items = [
            {
                "id": friend.id,
                "user_id":friend.candidate_id,

                "username": friend.user_name,
                "profile_image_url": friend.profile_image_url if friend.profile_image_url else None,
                "anonymous_id": friend.anonymous_id,
                "firstName": friend.first_name,
                "lastName": friend.last_name,
                "is_active": friend.is_active
            }
            for friend in suggestions
        ]

        return {
            "status": "SUCCESS",
            "status_code": "200",
            "data": items
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )
    
@router.post("/block/{friendship_id}", response_model=ApiSchema.ApiResponse)
async def update_user_profile_image(
    friendship_id: str,
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    '''
      To Block and unblock a specific user , if user is already block 
      it will unblock the user other wise Block the user.
    '''
    try:
      
        # Get the existing user and update their profile image
        user = db.query(models.Friendship).filter(
            models.Friendship.friend_id == friendship_id,
            models.Friendship.user_id == user_id
            ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Update only the profile image URL
        user.isBolcked = not user.isBolcked
        
        # Commit the changes
        db.commit()
        
        return {
            "status": "success",
            "message": f"User block sucessfully with with {user.friend_id}",
            "status_code": "200"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error while blocking user with id {user.friend_id}: {str(e)}"
        )
    


@router.post("/addHomies", response_model=ApiSchema.ApiResponse)
async def update_homies_status(
    friendship_ids: List[str],
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        # Keep track of successful and failed updates
        successful_updates = []
        failed_updates = []

        # Process each friendship ID in the list
        for friend_id in friendship_ids:
            try:
                # Get the existing friendship record
                friendship = db.query(models.Friendship).filter(
                    models.Friendship.friend_id == friend_id,
                    models.Friendship.user_id == user_id
                ).first()

                if friendship:
                    # Update the homies status
                    friendship.isHomies = True
                    successful_updates.append(friend_id)
                else:
                    failed_updates.append({
                        "friend_id": friend_id,
                        "reason": "Friendship not found"
                    })

            except Exception as friend_error:
                failed_updates.append({
                    "friend_id": friend_id,
                    "reason": str(friend_error)
                })

        # Commit all successful changes
        if successful_updates:
            db.commit()

        # Prepare the response message
        if successful_updates and not failed_updates:
            message = f"All {len(successful_updates)} users added successfully to the Homies List"
            status_code = 200
        elif successful_updates and failed_updates:
            message = f"{len(successful_updates)} users added successfully, {len(failed_updates)} failed"
            status_code = 207  # Partial Content
        else:
            message = "No users were added to the Homies List"
            status_code = 400

        return {
            "status": "success" if successful_updates else "error",
            "message": message,
            "status_code": str(status_code),
            "successful_updates": successful_updates,
            "failed_updates": failed_updates
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error while processing Homies List updates: {str(e)}"
        )

@router.post("/restrict/{friendship_id}", response_model=ApiSchema.ApiResponse)
async def update_user_profile_image(
    friendship_id: str,
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
       
        # Get the existing user and update their profile image
        user = db.query(models.Friendship).filter(
            models.Friendship.friend_id == friendship_id,
            models.Friendship.user_id == user_id
            ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Update only the profile image URL
        user.isRestricted = True
        
        # Commit the changes
        db.commit()
        
        return {
            "status": "success",
            "message": f"User {user.friend_id} add sucessfully Restricted",
            "status_code": "200"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error while Restricting {user.friend_id}: {str(e)}"
        )



@router.get("/friendRequest", response_model=ApiSchema.ApiResponse)
async def get_friend_requests(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = 'PENDING',
    current_user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        # Base query to get users who sent friend requests to current user
        query = (
            db.query(userModels.User)
            .join(
                models.Friendship,
                and_(
                    models.Friendship.friend_id == str(current_user_id),  # Convert to string if needed
                    models.Friendship.user_id == userModels.User.candidate_id
                )
            )
            .options(joinedload(userModels.User.friend_of))
        )

        # Apply status filter
        if status:
            query = query.filter(models.Friendship.status == status)

        # Apply search filter if provided
        if search:
            query = query.filter(userModels.User.user_name.ilike(f"%{search}%"))

        # Get total count
        total = query.count()

        # Get paginated results
        friends = (
            query
            # .order_by((models.Friendship.created_at))  # Latest requests first
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )

        # Format response
        items = [
            {
                "id": friend.id,
                "user_id":friend.candidate_id,
                "username": friend.user_name,
                "profile_image_url": friend.profile_image_url if friend.profile_image_url else None,
                "anonymous_id": friend.anonymous_id,
                "firstName": friend.first_name,
                "lastName": friend.last_name,
                "is_active": friend.is_active,
                "friendship_details": {
                    "isHomies": friend.friend_of[0].isHomies if friend.friend_of else False,
                    "isBlocked": friend.friend_of[0].isBlocked if friend.friend_of else False,
                    "isRestricted": friend.friend_of[0].isRestricted if friend.friend_of else False,
                    "created_at": friend.friend_of[0].created_at if friend.friend_of else None
                } if friend.friend_of else None
            }
            for friend in friends
        ]

        return {
            "status": "success",
            "status_code": "200",
            "data": items,
            "total": total,
            "page": page,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )