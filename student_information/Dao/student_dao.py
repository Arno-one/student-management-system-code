from sqlalchemy.orm import Session
from model import Student
from typing import List, Optional

# 定义一个类StudentDAO，专门管学生表的数据库操作
# 创建 StudentDAO 对象时，必须传入一个数据库会话 db
# 然后把它存到 self.db，后面所有方法都用它操作数据库
class StudentDAO:
    """学生信息数据访问对象"""

    # : 是 类型注解，db 这个变量，必须是 Session 类型的对象
    def __init__(self, db: Session):
        self.db = db

    # ==================== 增（CREATE）====================
    def create_from_dict(self, data: dict) -> Student:
        """通过字典新增学生"""
        student = Student(**data)
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        return student

    # ==================== 查（READ）====================
    def get_by_id(self, student_id: int) -> Optional[Student]:
        """根据ID查询（未删除）"""
        return self.db.query(Student).filter(
            Student.id == student_id,
            Student.is_deleted == 0
        ).first()

    def get_by_student_no(self, student_no: str) -> Optional[Student]:
        """根据学号查询"""
        return self.db.query(Student).filter(
            Student.student_no == student_no,
            Student.is_deleted == 0
        ).first()

    def get_all(
            self,
            page: int = 0,
            limit: int = 100,
            order_by: str = "id"  # 不传排序参数 → 默认自动按 id 排序
    ) -> List[Student]:
        # 分页查询所有未删除学生
        query = self.db.query(Student).filter(Student.is_deleted == 0)

        # 排序处理
        if hasattr(Student, order_by):
            query = query.order_by(getattr(Student, order_by))

        return query.offset(page*limit).limit(limit).all()

    def get_by_class(self, class_id: int) -> List[Student]:
        """查询班级下的学生"""
        return self.db.query(Student).filter(
            Student.class_id == class_id,
            Student.is_deleted == 0
        ).all()

    # **filters = 接收 “一堆关键字参数” 的特殊变量，打包成一个字典
    def search(self, **filters) -> List[Student]:
        """
        动态多条件查询
        支持参数：student_name, gender, min_age, max_age, class_id, education
        """
        query = self.db.query(Student).filter(Student.is_deleted == 0)

        if 'student_name' in filters and filters['student_name']:
            query = query.filter(Student.student_name.like(f"%{filters['student_name']}%"))
        if 'gender' in filters and filters['gender']:
            query = query.filter(Student.gender == filters['gender'])
        if 'min_age' in filters and filters['min_age']:
            query = query.filter(Student.age >= filters['min_age'])
        if 'max_age' in filters and filters['max_age']:
            query = query.filter(Student.age <= filters['max_age'])
        if 'class_id' in filters and filters['class_id']:
            query = query.filter(Student.class_id == filters['class_id'])
        if 'education' in filters and filters['education']:
            query = query.filter(Student.education == filters['education'])

        return query.all()

    def count(self) -> int:
        """统计未删除学生总数"""
        return self.db.query(Student).filter(Student.is_deleted == 0).count()

    # ==================== 改（UPDATE）====================
    def update(self, student_id: int, update_data: dict) -> Optional[Student]:
        """
        根据学生id更新学生信息（自动排除 id / student_no / create_time / is_deleted）
        """
        student = self.get_by_id(student_id)
        if not student:
            return None

        forbidden = {'id', 'student_no', 'create_time', 'is_deleted'}
        for key, value in update_data.items():
            if key not in forbidden and hasattr(student, key):
                setattr(student, key, value)

        self.db.commit()
        self.db.refresh(student)
        return student

    # ==================== 逻辑删除（DELETE）====================
    def soft_delete(self, student_id: int) -> bool:
        """
        逻辑删除单个学生
        返回 True/False 表示是否删除成功
        """
        student = self.get_by_id(student_id)
        if not student:
            return False

        student.is_deleted = 1
        self.db.commit()
        return True

    def batch_soft_delete(self, student_ids: List[int]) -> int:
        """批量逻辑删除，返回成功删除的数量"""
        result = self.db.query(Student).filter(
            Student.id.in_(student_ids),
            Student.is_deleted == 0
        ).update({Student.is_deleted: 1}, synchronize_session=False)
        # query 是一个 SQLAlchemy 查询对象，这个对象自带 .update() 方法，批量更新数据库数据，必须配合 query.filter () 使用
        # .update() 执行后，会自动返回会自动返回 受影响的行数
        # synchronize_session=False 更新完数据库，不同步内存数据，让批量更新更快、更安全、不报错

        self.db.commit()
        return result

    def restore(self, student_id: int) -> bool:
        """恢复已逻辑删除的学生"""
        student = self.db.query(Student).filter(
            Student.id == student_id,
            Student.is_deleted == 1
        ).first()
        if not student:
            return False

        student.is_deleted = 0
        self.db.commit()
        return True