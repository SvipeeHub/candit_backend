from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.models import Otp_model as models,User_model as userModels,Post_model as postModel
from app.util.generateJwt import create_jwt_token,verify_jwt_token
from app.schema import api_response_schema as schemas,post_schema as postSchema
from app.database import get_db
from datetime import datetime
import random
import string
import httpx
from collections import defaultdict

import os
router = APIRouter(prefix="/memories", tags=["memories"])

@router.post('/', response_model=schemas.ApiResponse)
def add_memories_to_highlight(
    request: postSchema.HighlightPostsRequest,
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Adding memories to the User Highlights
    """
    try:
        # Verify posts exist and belong to the user
        posts = db.query(postModel.Post).filter(
            postModel.Post.post_id.in_(request.post_ids),
            postModel.Post.user_id == user_id
        ).all()

        # Check if all requested posts were found
        found_post_ids = [post.post_id for post in posts]
        missing_post_ids = set(request.post_ids) - set(found_post_ids)
        
        if missing_post_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Posts with IDs {missing_post_ids} not found or don't belong to the user"
            )

        # Update isHighlighted status for all found posts
        for post in posts:
            post.isHighlighted = True

        db.commit()

        return {
            "status": "success",
            "message": f"Successfully highlighted {len(posts)} posts",
            "status_code": "201"
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error highlighting memories: {str(e)}"
        )

# Optional: Add an endpoint to remove highlights
@router.delete('/', response_model=schemas.ApiResponse)
def remove_memories_from_highlight(
    request: postSchema.HighlightPostsRequest,
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Remove memories from User Highlights
    """
    try:
        # Verify posts exist and belong to the user
        posts = db.query().filter(
            postModel.Post.post_id.in_(request.post_ids),
            postModel.Post.user_id == user_id
        ).all()

        # Check if all requested posts were found
        found_post_ids = [post.post_id for post in posts]
        missing_post_ids = set(request.post_ids) - set(found_post_ids)
        
        if missing_post_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Posts with IDs {missing_post_ids} not found or don't belong to the user"
            )

        # Update isHighlighted status for all found posts
        for post in posts:
            post.isHighlighted = False

        db.commit()

        return {
            "status": "success",
            "message": f"Successfully removed highlight from {len(posts)} posts",
            "status_code": "200"
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error removing highlights: {str(e)}"
        )
    

@router.get('/highlights', response_model=postSchema.HighlightedPostsResponse)
async def get_highlighted_memories(
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Get all highlighted posts grouped by year and month
    """
    try:
        # Fetch all highlighted posts for the user
        posts = db.query(postModel.Post).filter(
            postModel.Post.user_id == user_id,
            postModel.Post.isHighlighted == True
        ).order_by(
            postModel.Post.created_at.desc()
        ).all()

        if not posts:
            return {
                "status": "success",
                "message": "No highlighted posts found",
                "status_code": "200",
                "data": []
            }

        # Group posts by year and month
        year_month_posts = defaultdict(lambda: defaultdict(list))
        
        for post in posts:
            year = post.created_at.year
            month = post.created_at.month
            year_month_posts[year][month].append(post)

        # Format the response
        formatted_data = []
        
        # Month names mapping
        month_names = {
            1: "January", 2: "February", 3: "March", 
            4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September", 
            10: "October", 11: "November", 12: "December"
        }

        # Sort years in descending order
        for year in sorted(year_month_posts.keys(), reverse=True):
            monthly_data = []
            
            # Sort months in descending order
            for month in sorted(year_month_posts[year].keys(), reverse=True):
                monthly_posts = year_month_posts[year][month]
                
                monthly_data.append(postSchema.MonthlyPosts(
                    month=month,
                    month_name=month_names[month],
                    posts=[postSchema.PostResponse.from_orm(post) for post in monthly_posts]
                ))

            formatted_data.append(postSchema.YearlyPosts(
                year=year,
                months=monthly_data
            ))

        return {
            "status": "success",
            "message": "Highlighted posts retrieved successfully",
            "status_code": "200",
            "data": formatted_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error fetching highlighted posts: {str(e)}"
        )

# Optional: Add an endpoint to get posts for a specific year and month
@router.get('/highlights/{year}/{month}', response_model=postSchema.HighlightedPostsResponse)
async def get_highlighted_memories_by_month(
    year: int,
    month: int,
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Get highlighted posts for a specific year and month
    """
    try:
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(
                status_code=400,
                detail="Invalid month. Month must be between 1 and 12"
            )

        # Fetch posts for the specific month and year
        posts = db.query(postModel.Post).filter(
            postModel.Post.user_id == user_id,
            postModel.Post.isHighlighted == True,
            extract('year', postModel.Post.created_at) == year,
            extract('month', postModel.Post.created_at) == month
        ).order_by(
            postModel.Post.created_at.desc()
        ).all()

        if not posts:
            return {
                "status": "success",
                "message": f"No highlighted posts found for {month}/{year}",
                "status_code": "200",
                "data": []
            }

        month_names = {
            1: "January", 2: "February", 3: "March", 
            4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September", 
            10: "October", 11: "November", 12: "December"
        }

        formatted_data = [postSchema.YearlyPosts(
            year=year,
            months=[postSchema.MonthlyPosts(
                month=month,
                month_name=month_names[month],
                posts=[postSchema.PostResponse.from_orm(post) for post in posts]
            )]
        )]

        return {
            "status": "success",
            "message": "Highlighted posts retrieved successfully",
            "status_code": "200",
            "data": formatted_data
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error fetching highlighted posts: {str(e)}"
        )

@router.get('/all', response_model=postSchema.HighlightedPostsResponse)
async def get_highlighted_memories(
    user_id: int = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Get all the memories that user created till yet
    """
    try:
        # Fetch all highlighted posts for the user
        posts = db.query(postModel.Post).filter(
            postModel.Post.user_id == user_id,
            # postModel.Post.isHighlighted == True
        ).order_by(
            postModel.Post.created_at.desc()
        ).all()

        if not posts:
            return {
                "status": "success",
                "message": "No Momoreis found",
                "status_code": "200",
                "data": []
            }

        # Group posts by year and month
        year_month_posts = defaultdict(lambda: defaultdict(list))
        
        for post in posts:
            year = post.created_at.year
            month = post.created_at.month
            year_month_posts[year][month].append(post)

        # Format the response
        formatted_data = []
        
        # Month names mapping
        month_names = {
            1: "January", 2: "February", 3: "March", 
            4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September", 
            10: "October", 11: "November", 12: "December"
        }

        # Sort years in descending order
        for year in sorted(year_month_posts.keys(), reverse=True):
            monthly_data = []
            
            # Sort months in descending order
            for month in sorted(year_month_posts[year].keys(), reverse=True):
                monthly_posts = year_month_posts[year][month]
                
                monthly_data.append(postSchema.MonthlyPosts(
                    month=month,
                    month_name=month_names[month],
                    posts=[postSchema.PostResponse.from_orm(post) for post in monthly_posts]
                ))

            formatted_data.append(postSchema.YearlyPosts(
                year=year,
                months=monthly_data
            ))

        return {
            "status": "success",
            "message": "Momories retrieved successfully",
            "status_code": "200",
            "data": formatted_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error fetching Momories: {str(e)}"
        )
    


@router.get('/highlights/otheruser', response_model=postSchema.HighlightedPostsResponse)
async def get_highlighted_memories(
    user_id: str=None,
    db: Session = Depends(get_db)
):
    """
    Get all highlighted posts grouped by year and month of other user 
    """
    try:
        # Fetch all highlighted posts for the user
        posts = db.query(postModel.Post).filter(
            postModel.Post.user_id == user_id,
            postModel.Post.isHighlighted == True
        ).order_by(
            postModel.Post.created_at.desc()
        ).all()

        if not posts:
            return {
                "status": "success",
                "message": "No highlighted posts found",
                "status_code": "200",
                "data": []
            }

        # Group posts by year and month
        year_month_posts = defaultdict(lambda: defaultdict(list))
        
        for post in posts:
            year = post.created_at.year
            month = post.created_at.month
            year_month_posts[year][month].append(post)

        # Format the response
        formatted_data = []
        
        # Month names mapping
        month_names = {
            1: "January", 2: "February", 3: "March", 
            4: "April", 5: "May", 6: "June",
            7: "July", 8: "August", 9: "September", 
            10: "October", 11: "November", 12: "December"
        }

        # Sort years in descending order
        for year in sorted(year_month_posts.keys(), reverse=True):
            monthly_data = []
            
            # Sort months in descending order
            for month in sorted(year_month_posts[year].keys(), reverse=True):
                monthly_posts = year_month_posts[year][month]
                
                monthly_data.append(postSchema.MonthlyPosts(
                    month=month,
                    month_name=month_names[month],
                    posts=[postSchema.PostResponse.from_orm(post) for post in monthly_posts]
                ))

            formatted_data.append(postSchema.YearlyPosts(
                year=year,
                months=monthly_data
            ))

        return {
            "status": "success",
            "message": "Highlighted posts retrieved successfully",
            "status_code": "200",
            "data": formatted_data
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error fetching highlighted posts: {str(e)}"
        )