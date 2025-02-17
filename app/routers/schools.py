from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schema import school_schema  as schemas,api_response_schema as ApiSchema

from app.models import School_model as models,User_model as userModel
from app.database import get_db
from typing import List

router = APIRouter(prefix="/school", tags=["school"])

@router.post("/", response_model=ApiSchema.ApiResponse)
def create_school(user: schemas.CreateSchoolRequest, db: Session = Depends(get_db)):
   '''
       Adding the school to the data base 
   '''
   try:
       db_school = models.School(
            school_name = user.school_name,
    school_address = user.school_address,
    school_city = user.school_city,
    school_state = user.school_state
       )
       db.add(db_school)
       db.commit()
       db.refresh(db_school)
       
       return {
           "status": "success",
           "message": "School added successfully",
           "status_code": "201"
       }
       
   except Exception as e:
       db.rollback()
       raise HTTPException(
           status_code=400,
           detail=f"Error creating user: {str(e)}"
       )


@router.get("/", response_model=ApiSchema.ApiResponse)
def get_schools(db: Session = Depends(get_db)):
    '''
            This will return the all school that are in our data base
            1. count the user that is related to that specific school
    
    '''
    try:
        schools = db.query(models.School).all()
        school_data = []
        for school in schools:
            student_count = db.query(userModel.User).filter(
                userModel.User.school_id == school.school_id
            ).count()
            
            school_dict = {
                "id": school.id,
                "school_id": school.school_id,
                "school_name": school.school_name,
                "school_address": school.school_address,
                "school_city": school.school_city,
                "school_state": school.school_state,
                "student_count": student_count
            }
            school_data.append(school_dict)

        return {
            "status": "success",
            "message": "Schools retrieved successfully",
            "status_code": "200",
            "data": school_data
        }
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error retrieving schools: {str(e)}"
        )