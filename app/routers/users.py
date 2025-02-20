from fastapi import APIRouter, Depends, HTTPException , File , UploadFile,Query
from sqlalchemy.orm import Session,joinedload
from app.util.generateJwt import create_jwt_token,verify_jwt_token
from app.schema import User_schema as schemas , api_response_schema as ApiSchema
from app.models import User_model as models,Post_restriction_model as PostRestrictionModel,Post_model as postModel
from app.database import get_db
from typing import List
from app.util.saveFiles import create_upload_dir, save_upload_file, ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES
from typing import Optional, List
import os
router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=ApiSchema.ApiResponse)
async def create_user(user: schemas.User, db: Session = Depends(get_db)):
   try:
       
       db_user = models.User(
           email=user.email,
           phone=user.phone,
           user_name=user.userName,
           first_name=user.firstName,
           last_name=user.lastName,
           anonymous_id=user.anonymousId,
           dob=user.dob,
           batch=user.batch,
           course=user.course,
           school_id=user.schoolId
       )
       db.add(db_user)
       db.commit()
       db.refresh(db_user)
       
       return {
           "status": "success",
           "message": "User created successfully",
           "status_code": "201",
           "data":[{
               "user_id":db_user.candidate_id,
               "token":create_jwt_token(db_user.candidate_id)
           }]
       }
       
   except Exception as e:
       db.rollback()
       raise HTTPException(
           status_code=400,
           detail=f"Error creating user: {str(e)}"
       )
   
@router.get("/",response_model=ApiSchema.ApiResponse)
async def get_userDetails(db:Session=Depends(get_db),user_id:str = Depends(verify_jwt_token)):
    try:
        user =db.query(models.User).filter(
            models.User.candidate_id == user_id
        ).first()
       
        if not user:
           raise HTTPException(status_code=404, detail="User not found")
        user_data = {k: v for k, v in user.__dict__.items() if not k.startswith('_')}
        user_data['school'] = {k: v for k, v in user.school.__dict__.items() if not k.startswith('_')}
        return {
           "status": "success",
           "message": "User Data fetched Successfully",
           "status_code": "200",
           "data":[user_data]
       }
    except Exception as e:
       raise HTTPException(
           status_code=400,
           detail=f"Error creating user: {str(e)}"
       )


# Adding the profile Image of the User

@router.post("/profilePic", response_model=ApiSchema.ApiResponse)
async def update_user_profile_image(
    profileImage: Optional[UploadFile] = File(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        # Save the uploaded file
        file_path = await save_upload_file(profileImage, "image")
        post_url = f"/uploads/images/{os.path.basename(file_path)}"
    
        # Get the existing user and update their profile image
        user = db.query(models.User).filter(models.User.candidate_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Update only the profile image URL
        user.profile_image_url = post_url
        
        # Commit the changes
        db.commit()
        
        return {
            "status": "success",
            "message": "Profile picture updated successfully",
            "status_code": "201"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error while updating profile pic: {str(e)}"
        )

@router.post("/anonymousId", response_model=ApiSchema.ApiResponse)
async def update_user_profile_image(
    anonymousID: str,
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
       
        # Get the existing user and update their profile image
        user = db.query(models.User).filter(models.User.candidate_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Update only the profile image URL
        user.anonymous_id = anonymousID
        
        # Commit the changes
        db.commit()
        
        return {
            "status": "success",
            "message": "Anonymous Id updated Sucessfully",
            "status_code": "201"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error while updating anonymous ID: {str(e)}"
        )

@router.post("/post-restriction/comrades", response_model=ApiSchema.ApiResponse)
async def add_comrades_restrictions(
    request: schemas.HiddenUsersRequest,
    current_user: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
        Adding the user it to the Comrades Hide from list
    """
    try:
        # Get or create user post restriction
        post_restriction = db.query(PostRestrictionModel.PostRestriction).filter(
            PostRestrictionModel.PostRestriction.user_id== current_user
        ).first()
        
        if not post_restriction:
            # Create new restriction entry if it doesn't exist
            post_restriction = PostRestrictionModel.PostRestriction(
                user_id=current_user,
                comrades_hidden_from=[],
                public_hidden_from=[]
            )
            db.add(post_restriction)
            db.commit()
            db.refresh(post_restriction)
        
        # Update comrades_hidden_from array
        current_hidden = post_restriction.comrades_hidden_from or []
        post_restriction.comrades_hidden_from = list(set(current_hidden + request.hidden_user_ids))
        
        # Commit changes
        
        db.commit()
        return {
            "status": "success",
            "status_code":"201",
            "message": f"Successfully added {len(request.hidden_user_ids)} users to comrades hidden list",
            # "data": post_restriction
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error updating comrades restrictions: {str(e)}"
        )

@router.post("/post-restriction/public", response_model=ApiSchema.ApiResponse)
async def add_public_restrictions(
    request: schemas.HiddenUsersRequest,
    current_user: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
        Adding the User Id to the PUblic Hide From 
    """
    try:
        # Get or create user post restriction
        post_restriction = db.query(PostRestrictionModel.PostRestriction).filter(
            PostRestrictionModel.PostRestriction.user_id == current_user
        ).first()
        
        if not post_restriction:
            # Create new restriction entry if it doesn't exist
            post_restriction = PostRestrictionModel.PostRestriction(
                user_id=current_user,
                comrades_hidden_from=[],
                public_hidden_from=[]
            )
            db.add(post_restriction)
        
        # Update public_hidden_from array
        current_hidden = post_restriction.public_hidden_from or []
        post_restriction.public_hidden_from = list(set(current_hidden + request.hidden_user_ids))
        
        # Commit changes
        db.commit()
        db.refresh(post_restriction)
        
        return {
            "status": "success",
            "status_code":"201",
            "message": f"Successfully added {len(request.hidden_user_ids)} users to public hidden list",
            # "data": post_restriction
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error updating public restrictions: {str(e)}"
        )
    
@router.post("/check_user_Name", response_model=ApiSchema.ApiResponse)
async def check_username(
    request: dict,  # Assuming you'll send username in request
    db: Session = Depends(get_db)
):
    """
    Check if username exists in the database
    """
    try:
        # Extract username from request
        username = request.get('username')
        
        if not username:
            raise HTTPException(
                status_code=400,
                detail="Username is required"
            )
        
        # Query the database to check if username exists
        # Note: Replace UserModel with your actual user model
        user_exists = db.query(models.User).filter(
            models.User.user_name == username
        ).first()
        
        return {
            "status": "success",
            "status_code": "200",
            "message": "Username availability checked successfully",
            "data": [{
                "username": username,
                "is_available": not bool(user_exists)
            }]
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error checking username: {str(e)}"
        )


@router.get("/otherProfile", response_model=ApiSchema.ApiResponse)
async def get_userDetails(
    db: Session = Depends(get_db),
    user_id: str = None
):
    try:
        user = (
            db.query(models.User)
            .options(
                joinedload(models.User.school),
                joinedload(models.User.posts)
            )
            .filter(models.User.candidate_id == user_id)
            .first()
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Format user data excluding relationships and internal fields
        user_data = {
            "id": user.id,
            "user_id": user.candidate_id,
            "user_name": user.user_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            'dob':user.dob,
            'course':user.course,
            'batch':user.batch,
            "phone": user.phone,
            "profile_image_url": user.profile_image_url,
            "anonymous_id": user.anonymous_id,
            "is_active": user.is_active,
            "created_at": str(user.created_at) if user.created_at else None,
        }

        # Add school data if exists
        if user.school:
            user_data['school'] = {
                "id": user.school.id,
                "school_name": user.school.school_name,
                "school_address": user.school.school_address,
                "school_city":user.school.school_city
            }

        # Format highlighted posts
        user_data['highlighted_posts'] = [
            {
                "id": post.id,
                "post_type": post.post_type,
                "post_url": post.post_url,
                "caption": post.caption,
                "thumbnail": post.thumbnail,
                "is_anonymous": post.is_anonymous,
                "hash_tags": post.hash_tags if hasattr(post, 'hash_tags') else [],
                "language": post.language if hasattr(post, 'language') else [],
            }
            for post in user.posts
            if getattr(post, 'isHighlighted', True)
        ]

        return {
            "status": "success",
            "message": "User Data fetched Successfully",
            "status_code": "200",
            "data": [user_data]
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error fetching user data: {str(e)}"
        )

@router.post("/update/accountType", response_model=ApiSchema.ApiResponse)
async def update_account_type(
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Toggle the account type between public and private
    """
    try:
        # Get the existing user
        user = db.query(models.User).filter(models.User.candidate_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Toggle the is_active status (Python uses 'not' instead of '!')
        user.is_active = not user.is_active
        
        # Commit the changes
        db.commit()
        
        current_status = "private" if user.is_active else "public"
        
        return {
            "status": "success",
            "message": f"Account type updated to {current_status} successfully",
            "status_code": "201"
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error while updating account type: {str(e)}"
        )