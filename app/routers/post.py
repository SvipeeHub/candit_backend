from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form,Query
from sqlalchemy import and_ , or_
from sqlalchemy.orm import Session
from app.models import Post_model as models,User_model as user_Model, Friendship_model as friendship_model
from app.util.generateJwt import verify_jwt_token
from app.schema import api_response_schema as schemas, post_schema as postSchema,friends_schema 
from app.database import get_db
from app.util.saveFiles import create_upload_dir, save_upload_file, ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES
import os
import json
from typing import Optional, List

router = APIRouter(prefix="/post", tags=["post"])

@router.post('/', response_model=schemas.ApiResponse)
async def create_post(
    post_type: str = Form(...),
    file: Optional[UploadFile] = File(None),
    caption: Optional[str] = Form(None),
    is_anonymous: bool = Form(False),
    hash_tags: str = Form("[]"),
    language: str = Form("[]"),
    thumbnail: Optional[UploadFile] = File(None),
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        create_upload_dir()
        
        if post_type not in ["video", "image", "text"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid post type. Must be video, image, or text"
            )
            
        post_url = None
        post_poster_url = None
        
        if post_type in ["video", "image"]:
            if not file:
                raise HTTPException(
                    status_code=400,
                    detail=f"{post_type} post requires a file upload"
                )
                
            allowed_types = ALLOWED_IMAGE_TYPES if post_type == "image" else ALLOWED_VIDEO_TYPES
            
            if file.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {post_type} file type. Allowed types: {allowed_types}"
                )
                
            # Save the main file
            file_path = await save_upload_file(file, post_type)
            post_url = f"/uploads/{post_type}s/{os.path.basename(file_path)}"
            
            # Handle thumbnail for videos
            if post_type == "video" and thumbnail:
                if thumbnail.content_type not in ALLOWED_IMAGE_TYPES:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid thumbnail file type"
                    )
                thumbnail_path = await save_upload_file(thumbnail, "image")
                post_poster_url = f"/uploads/images/{os.path.basename(thumbnail_path)}"
        
        try:
            # Parse JSON strings for tags and languages with error handling
            hash_tags_list = json.loads(hash_tags) if hash_tags else []
            language_list = json.loads(language) if language else []
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON format for hash_tags or language"
            )
        
        # Create new post
        new_post = models.Post(
            post_type=post_type,
            post_url=post_url,
            caption=caption,
            thumbnail=post_poster_url,
            is_anonymous=is_anonymous,
            hash_tags=hash_tags_list,
            language=language_list,
            user_id=user_id
        )
        
        db.add(new_post)
        db.commit()
        db.refresh(new_post)
        
        return {
            "status": "success",
            "message": "Post created successfully",
            "status_code": "201"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error creating post: {str(e)}"
        )

@router.get('/', response_model=schemas.ApiResponse)
async def get_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        offset = (page - 1) * limit

        # Modified query with proper friendship join
        posts_query = (
            db.query(models.Post, user_Model.User, user_Model.Friendship)
            .join(user_Model.User, models.Post.user_id == user_Model.User.candidate_id)
            .outerjoin(
                user_Model.Friendship,
                and_(
                    or_(
                        and_(
                            user_Model.Friendship.user_id == str(current_user_id),
                            user_Model.Friendship.friend_id == models.Post.user_id
                        ),
                        and_(
                            user_Model.Friendship.friend_id == str(current_user_id),
                            user_Model.Friendship.user_id == models.Post.user_id
                        )
                    )
                )
            )
            .order_by(models.Post.created_at.desc())
        )

        total_posts = posts_query.count()
        posts_with_details = posts_query.offset(offset).limit(limit).all()

        posts_data = []
        for post, user, friendship in posts_with_details:
            relationship_data = None
            if current_user_id != user.id:
                print(friendship.status if friendship else None)
                relationship_data = {
                    "is_comrade": friendship.status.value == 'accepted' if friendship else False,
                    "is_homies": friendship.isHomies if friendship else False,
                    "is_blocked": friendship.isBolcked if friendship else False,
                    "is_restricted": friendship.isRestricted if friendship else False,
                    "status": friendship.status if friendship else None
                }

            post_data = {
                "post": {
                    "id": post.id,
                    "post_type": post.post_type,
                    "post_url": post.post_url,
                    "caption": post.caption,
                    "thumbnail": post.thumbnail,
                    "is_anonymous": post.is_anonymous,
                    "hash_tags": post.hash_tags,
                    "language": post.language,
                    "created_at": post.created_at,
                    "updated_at": post.updated_at
                },
                "user": {
                    "id": user.id,
                    "username": user.user_name,
                    "profile_image_url": user.profile_image_url,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "anonymous_id": user.anonymous_id if post.is_anonymous else None
                },
                "relationship": relationship_data
            }
            posts_data.append(post_data)

        return {
            "status": "success",
            "status_code": "200",
            "data": [{
                "posts": posts_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": (total_posts + limit - 1) // limit,
                    "total_posts": total_posts,
                    "has_next": offset + limit < total_posts,
                    "has_previous": page > 1
                }
            }]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching posts: {str(e)}"
        )