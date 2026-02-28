from fastapi import APIRouter
from app.api.v1 import auth, users, health, line_auth, line_notifications, courses, bookings, student_contracts, teacher_contracts, teacher_slots, student_courses

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(health.router)
api_router.include_router(line_auth.router)
api_router.include_router(line_notifications.router)
api_router.include_router(courses.router)
api_router.include_router(bookings.router)
api_router.include_router(student_courses.router)
api_router.include_router(student_contracts.router)
api_router.include_router(teacher_contracts.router)
api_router.include_router(teacher_slots.router)