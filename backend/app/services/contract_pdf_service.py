import os
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from app.services.supabase_service import supabase_service

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

STATUS_LABELS = {
    "pending": "待生效",
    "active": "生效中",
    "expired": "已過期",
    "terminated": "已終止",
}

STUDENT_DETAIL_TYPE_LABELS = {
    "lesson_price": "課程單價",
    "discount": "優惠折扣",
    "compensation": "補償堂數",
}

TEACHER_DETAIL_TYPE_LABELS = {
    "course_rate": "課程費率",
    "base_salary": "底薪",
    "allowance": "津貼",
}

EMPLOYMENT_TYPE_LABELS = {
    "hourly": "時薪",
    "full_time": "正職",
}

WEEKDAY_LABELS = {
    0: "週一",
    1: "週二",
    2: "週三",
    3: "週四",
    4: "週五",
    5: "週六",
    6: "週日",
}


async def _fetch_student_contract_data(contract_id: str) -> dict:
    """查詢學生合約 + 明細 + 關聯名稱"""
    result = await supabase_service.table_select(
        table="student_contracts",
        select="id,contract_no,student_id,contract_status,start_date,end_date,total_lessons,remaining_lessons,total_amount,total_leave_allowed,is_recurring,notes",
        filters={"id": contract_id, "is_deleted": "eq.false"},
    )
    if not result:
        return None

    contract = result[0]

    # 學生名稱
    if contract.get("student_id"):
        student = await supabase_service.table_select(
            table="students", select="name",
            filters={"id": contract["student_id"]},
        )
        contract["student_name"] = student[0]["name"] if student else None

    # 明細
    details = await supabase_service.table_select(
        table="student_contract_details",
        select="id,detail_type,course_id,description,amount",
        filters={
            "student_contract_id": f"eq.{contract_id}",
            "is_deleted": "eq.false",
        },
    )
    for d in details:
        if d.get("course_id"):
            course = await supabase_service.table_select(
                table="courses", select="course_name",
                filters={"id": d["course_id"]},
            )
            d["course_name"] = course[0]["course_name"] if course else None

    return {"contract": contract, "details": details}


async def _fetch_teacher_contract_data(contract_id: str) -> dict:
    """查詢教師合約 + 明細 + 工作時段 + 關聯名稱"""
    result = await supabase_service.table_select(
        table="teacher_contracts",
        select="id,contract_no,teacher_id,contract_status,start_date,end_date,employment_type,trial_completed_bonus,trial_to_formal_bonus,notes",
        filters={"id": contract_id, "is_deleted": "eq.false"},
    )
    if not result:
        return None

    contract = result[0]

    # 教師名稱
    if contract.get("teacher_id"):
        teacher = await supabase_service.table_select(
            table="teachers", select="name",
            filters={"id": contract["teacher_id"]},
        )
        contract["teacher_name"] = teacher[0]["name"] if teacher else None

    # 明細
    details = await supabase_service.table_select(
        table="teacher_contract_details",
        select="id,detail_type,course_id,description,amount",
        filters={
            "teacher_contract_id": f"eq.{contract_id}",
            "is_deleted": "eq.false",
        },
    )
    for d in details:
        if d.get("course_id"):
            course = await supabase_service.table_select(
                table="courses", select="course_name",
                filters={"id": d["course_id"]},
            )
            d["course_name"] = course[0]["course_name"] if course else None

    # 工作時段
    work_schedules = await supabase_service.table_select(
        table="teacher_work_schedules",
        select="id,weekday,start_time,end_time,notes",
        filters={
            "teacher_contract_id": f"eq.{contract_id}",
            "is_deleted": "eq.false",
        },
    )

    return {"contract": contract, "details": details, "work_schedules": work_schedules}


async def generate_student_contract_pdf(contract_id: str) -> tuple[bytes, str] | None:
    """產生學生合約 PDF，回傳 (pdf_bytes, contract_no) 或 None"""
    data = await _fetch_student_contract_data(contract_id)
    if not data:
        return None

    template = env.get_template("student_contract.html")
    html_str = template.render(
        contract=data["contract"],
        details=data["details"],
        status_label=STATUS_LABELS.get(data["contract"]["contract_status"], data["contract"]["contract_status"]),
        detail_type_labels=STUDENT_DETAIL_TYPE_LABELS,
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes, data["contract"]["contract_no"]


async def generate_addendum_pdf(addendum_id: str) -> tuple[bytes, str] | None:
    """產生附約 PDF，回傳 (pdf_bytes, addendum_no) 或 None"""
    result = await supabase_service.table_select(
        table="contract_addendums",
        select="id,addendum_no,contract_type,parent_contract_id,original_end_date,new_end_date,addendum_status,notes",
        filters={"id": addendum_id, "is_deleted": "eq.false"},
    )
    if not result:
        return None

    addendum = result[0]
    contract_type = addendum["contract_type"]

    # 取得母約編號和人名
    if contract_type == "student":
        parent = await supabase_service.table_select(
            table="student_contracts",
            select="contract_no,student_id",
            filters={"id": addendum["parent_contract_id"], "is_deleted": "eq.false"},
        )
        if not parent:
            return None
        parent_contract_no = parent[0]["contract_no"]
        person_name = None
        if parent[0].get("student_id"):
            student = await supabase_service.table_select(
                table="students", select="name",
                filters={"id": parent[0]["student_id"]},
            )
            person_name = student[0]["name"] if student else None
        title = "學生"
        person_label = "學生"
    else:
        parent = await supabase_service.table_select(
            table="teacher_contracts",
            select="contract_no,teacher_id",
            filters={"id": addendum["parent_contract_id"], "is_deleted": "eq.false"},
        )
        if not parent:
            return None
        parent_contract_no = parent[0]["contract_no"]
        person_name = None
        if parent[0].get("teacher_id"):
            teacher = await supabase_service.table_select(
                table="teachers", select="name",
                filters={"id": parent[0]["teacher_id"]},
            )
            person_name = teacher[0]["name"] if teacher else None
        title = "教師"
        person_label = "教師"

    template = env.get_template("contract_addendum.html")
    html_str = template.render(
        addendum=addendum,
        title=title,
        person_label=person_label,
        parent_contract_no=parent_contract_no,
        person_name=person_name,
        status_label=STATUS_LABELS.get(addendum["addendum_status"], addendum["addendum_status"]),
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes, addendum["addendum_no"]


async def generate_teacher_contract_pdf(contract_id: str) -> tuple[bytes, str] | None:
    """產生教師合約 PDF，回傳 (pdf_bytes, contract_no) 或 None"""
    data = await _fetch_teacher_contract_data(contract_id)
    if not data:
        return None

    template = env.get_template("teacher_contract.html")
    html_str = template.render(
        contract=data["contract"],
        details=data["details"],
        work_schedules=data["work_schedules"],
        status_label=STATUS_LABELS.get(data["contract"]["contract_status"], data["contract"]["contract_status"]),
        employment_type_label=EMPLOYMENT_TYPE_LABELS.get(data["contract"].get("employment_type", ""), "-"),
        detail_type_labels=TEACHER_DETAIL_TYPE_LABELS,
        weekday_labels=WEEKDAY_LABELS,
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes, data["contract"]["contract_no"]
