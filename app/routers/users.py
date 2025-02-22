from fastapi import APIRouter, Depends, HTTPException , File , UploadFile,Query
from sqlalchemy.orm import Session,joinedload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_, or_, not_
from app.util.generateJwt import create_jwt_token,verify_jwt_token
from app.schema import User_schema as schemas , api_response_schema as ApiSchema,friends_schema as freindSchema
from app.models import User_model as models,Post_restriction_model as PostRestrictionModel,Post_model as postModel,Contact_list as contactModel,Stalked_profile as stalkModel
from app.database import get_db
from typing import List
from app.util.saveFiles import create_upload_dir, save_upload_file, ALLOWED_IMAGE_TYPES, ALLOWED_VIDEO_TYPES
from typing import Optional, List
import os,re,logging
from app.util import helperFunctions as hf
logger = logging.getLogger(__name__)

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


@router.post("/users/contacts/", response_model=List[schemas.Contact])
async def create_user_contacts(
    contact_list: schemas.ContactListCreate,
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        # Check if user exists
        db_user = db.query(models.User).filter(models.User.candidate_id == user_id).first()
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate phone numbers
        for contact in contact_list.contacts:
            if not hf.is_valid_phone_number(contact.phone_number):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid phone number format: {contact.phone_number}"
                )
        
        created_contacts = []
        
        # Start transaction
        try:
            # Create each contact in the list
            for contact_data in contact_list.contacts:
                # Check if contact already exists
                existing_contact = db.query(contactModel.Contact.Contact).filter(
                    contactModel.Contact.user_id == user_id,
                    contactModel.Contact.phone_number == contact_data.phone_number
                ).first()
                
                if existing_contact:
                    # Update existing contact
                    existing_contact.name = contact_data.name
                    created_contacts.append(existing_contact)
                else:
                    # Create new contact
                    db_contact = contactModel.Contact(
                        name=contact_data.name,
                        phone_number=contact_data.phone_number,
                        user_id=user_id
                    )
                    db.add(db_contact)
                    created_contacts.append(db_contact)
            
            # Commit transaction
            db.commit()
            
            # Refresh all contacts to get their IDs
            for contact in created_contacts:
                db.refresh(contact)
            
            return created_contacts
            
        except SQLAlchemyError as db_error:
            # Rollback in case of database error
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Database error occurred while creating contacts"
            ) from db_error
            
    except HTTPException as http_error:
        # Re-raise HTTP exceptions
        raise http_error
        
    except Exception as e:
        # Log unexpected errors and return generic error message
        logger.error(f"Unexpected error in create_user_contacts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        ) from e







@router.get("/name-suggestions", response_model=ApiSchema.ApiResponse)
async def get_name_suggestions(
    total_count: int = Query(12, description="Total number of names to return"),
    user_id: str = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    try:
        suggestions = []
        remaining_count = total_count

        def filter_by_gender(users, target_count):
            male_users = [u for u in users if u.gender == 'male']
            female_users = [u for u in users if u.gender == 'female']
            
            per_gender = target_count // 2
            result = (male_users[:per_gender] if len(male_users) >= per_gender else male_users) + \
                    (female_users[:per_gender] if len(female_users) >= per_gender else female_users)
            return result[:target_count]

        # 1. Get comrades (friends in both directions)
        comrades_as_user = db.query(models.User).join(
            models.Friendship,
            models.Friendship.friend_id == models.User.candidate_id
        ).filter(
            models.Friendship.user_id == user_id,
            models.Friendship.status == 'ACCEPTED',
            models.Friendship.isBolcked == False,
            models.Friendship.isRestricted == False
        )

        comrades_as_friend = db.query(models.User).join(
            models.Friendship,
            models.Friendship.user_id == models.User.candidate_id
        ).filter(
            models.Friendship.friend_id == user_id,
            models.Friendship.status == 'ACCEPTED',
            models.Friendship.isBolcked == False,
            models.Friendship.isRestricted == False
        )

        # Combine both queries using union
        comrades = comrades_as_user.union(comrades_as_friend).all()
        
        # Get comrades IDs for later use (include both directions)
        comrade_ids = [c.candidate_id for c in comrades]
        
        comrades = filter_by_gender(comrades, total_count)
        suggestions.extend([
            {
                "user_id": user.candidate_id,
                "name": f"{user.first_name} {user.last_name}",
                "suggestion_type": "comrade",
                "gender": user.gender,
                "profile_image_url": user.profile_image_url,
                "is_app_user": True
            } for user in comrades
        ])
        
        remaining_count -= len(suggestions)

        if remaining_count > 0:
            # 2. Get friends of friends (up to 30% of remaining)
            fof_limit = min(remaining_count, int(total_count * 0.3))
            
            # Modified friends of friends query to consider both friendship directions
            fof_users = db.query(models.User).join(
                models.Friendship,
                (models.Friendship.friend_id == models.User.candidate_id) |
                (models.Friendship.user_id == models.User.candidate_id)
            ).filter(
                (models.Friendship.user_id.in_(comrade_ids) |
                 models.Friendship.friend_id.in_(comrade_ids)),
                models.Friendship.status == 'ACCEPTED',
                models.Friendship.isBolcked == False,
                ~models.User.candidate_id.in_([s["user_id"] for s in suggestions]),
                models.User.candidate_id != user_id
            ).distinct().limit(fof_limit).all()
            
            fof_users = filter_by_gender(fof_users, fof_limit)
            suggestions.extend([
                {
                    "user_id": user.candidate_id,
                    "name": f"{user.first_name} {user.last_name}",
                    "suggestion_type": "friend_of_friend",
                    "gender": user.gender,
                    "profile_image_url": user.profile_image_url,
                    "is_app_user": True
                } for user in fof_users
            ])
            
            remaining_count -= len(fof_users)

        if remaining_count > 0:
            # 3. Get common contacts between user and their comrades
            # First get user's contacts
            user_contacts = db.query(contactModel.Contact.phone_number).filter(
                contactModel.Contact.user_id == user_id
            ).scalar_subquery()  # Use scalar_subquery() for single column subqueries

            # Get comrades' contacts that match user's contacts
            common_contacts = db.query(contactModel.Contact).join(
                models.User,
                models.User.candidate_id == contactModel.Contact.user_id
            ).filter(
                models.User.candidate_id.in_(comrade_ids),
                contactModel.Contact.phone_number.in_(
                    user_contacts
                )
            ).distinct(contactModel.Contact.phone_number).limit(remaining_count).all()

            suggestions.extend([
                {
                    "user_id": contact.phone_number,
                    "name": contact.name,
                    "suggestion_type": "common_contact",
                    "gender": "unknown",
                    "profile_image_url": None,
                    "is_app_user": False
                } for contact in common_contacts
            ])

        return {
            "status": "success",
            "message": "Name suggestions retrieved successfully",
            "status_code": 200,
            "data": suggestions
        }

    except Exception as e:
        logger.error(f"Error in get_name_suggestions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while getting name suggestions"
        )