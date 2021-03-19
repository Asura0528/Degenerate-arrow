from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


# 用户信息
class User(AbstractUser):
    # 电话号码字段
    # 作为唯一性字段
    mobile = models.CharField(max_length=11, unique=True, blank=False)

    # 头像
    # upload_to为保存到响应的子目录中
    avatar = models.ImageField(upload_to='avatar/%Y%m%d/', blank=True)

    # 个人简介
    user_desc = models.CharField(max_length=50, blank=True)

    # 修改认证的字段
    USERNAME_FIELD = 'mobile'

    # 创建超级管理员需要输入的字段
    REQUIRED_FIELDS = ['username', 'email']

    # 内部类 class Meta用于给model定义元数据
    class Meta:
        db_table = 'tb_users'    # 修改默认的表名
        verbose_name = '用户管理'   # Admin后台显示
        verbose_name_plural = verbose_name  # Admin后台显示

    def __str__(self):
        return self.mobile
