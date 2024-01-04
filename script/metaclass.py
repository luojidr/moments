import inspect


class ClassType(type):
    ctmx = 100

    def __new__(cls, name, bases, attrs, **kwargs):
        new_cls = super().__new__(cls, name, bases, attrs, **kwargs)
        print("new_cls:", name, new_cls, new_cls.__dict__)
        print(getattr(new_cls, "add_to_class"))
        return new_cls

    # 元类拥有的所有属性和方法，由改元类创建的子类都拥有
    def add_to_class(cls, name):
        pass


class ClassBase(metaclass=ClassType):
    @classmethod
    def get_pk(cls, pk):
        pass


class MyClass(ClassBase):
    def save(self):
        pass


print("MyClass:", getattr(MyClass, "add_to_class"))
results = inspect.getmembers(MyClass)
print(results)
print(MyClass.ctmx)
