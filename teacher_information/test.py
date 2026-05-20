from model import Teacher

if __name__=="__main__":
    Teacher.Base.metadata.create_all(Teacher.engine)