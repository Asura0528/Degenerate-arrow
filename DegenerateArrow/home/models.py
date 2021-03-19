from django.db import models
from django.utils import timezone
from users.models import User
from django.core.validators import MaxValueValidator, MinValueValidator


# Create your models here.
class ArticleCategory(models.Model):
    """
    文章分类
    """
    # 标题栏目
    title = models.CharField(max_length=100, blank=True)
    # 创建时间
    created = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'tb_category'
        verbose_name = '类别管理'
        verbose_name_plural = verbose_name


class CarouselImg(models.Model):
    """
    轮播图
    """
    # 轮播图图片
    carousel_img = models.ImageField(upload_to='carousel/%Y%m%d')
    is_first = models.BooleanField(blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        db_table = 'tb_carousel_img'
        verbose_name = '轮播图片管理'
        verbose_name_plural = verbose_name


class Article(models.Model):
    """
    文章
    """
    # 定义帖子作者。author通过models.ForeignKey外键与内键的User模型关联在一起
    # 参数on_delete用于指定数据删除的方式，避免两个关联表的数据不一致
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    # 帖子标题图片
    avatar = models.ImageField(upload_to='article/%Y%m%d/', blank=True)
    # 帖子栏目的“一对多”外键
    category = models.ForeignKey(
        ArticleCategory,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='article'
    )
    # 帖子标题
    title = models.CharField(max_length=100, null=False, blank=True)
    # 帖子简介
    sumary = models.CharField(max_length=200, null=False, blank=True)
    # 帖子正文
    content = models.TextField()
    # 浏览量
    total_views = models.PositiveIntegerField(default=0)
    # 评论数
    comments_count = models.PositiveIntegerField(default=0)
    # 帖子创建时间
    # 参数default = timezone.now指定其在创建数据时默认写入当前时间
    created = models.DateTimeField(default=timezone.now)
    # 文章更新时间
    # 参数auto_now = True指定每次数据更新时自动写入当前时间
    updated = models.DateTimeField(auto_now=True)
    # 帖子推荐
    recommend = models.BooleanField(blank=True)

    # 内部类，用于给model定义元数据
    class Meta:
        # ordering 指定模型返回的数据的排列顺序
        # '-created'表明数据应以倒序排列
        ordering = ('-created',)
        db_table = 'tb_article'
        verbose_name = '帖子管理'
        verbose_name_plural = verbose_name

    # 函数 __str__ 定义当调用对象的 str() 方法时的返回值内容
    # 它最常见的就是在Django管理后台中做为对象的显示值。因此应该总是为 __str__ 返回一个友好易读的字符串
    def __str__(self):
        # 将文章标题返回
        return self.title


class Comment(models.Model):
    # 评论内容
    content = models.TextField()
    # 评论的文章
    article = models.ForeignKey(Article,
                                on_delete=models.CASCADE)
    # 发表评论的用户
    user = models.ForeignKey('users.User',
                             on_delete=models.CASCADE)
    # 评论发布时间
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.article.title

    class Meta:
        db_table = 'tb_comment'
        verbose_name = '评论管理'
        verbose_name_plural = verbose_name


class PublicOffering(models.Model):
    """
    公开招募工具
    """
    # 干员代号
    agent_name = models.CharField(max_length=5)
    # 干员图片
    agent_img = models.ImageField(upload_to='agent/thumbnail/%Y%m%d')
    # 干员等级
    agent_level = models.IntegerField(
        default=1,
        validators=[MaxValueValidator(6), MinValueValidator(1)],
    )

    def __str__(self):
        return self.agent_name

    class Meta:
        db_table = 'tb_public_offering_agent'
        verbose_name = '公开招募干员管理'
        verbose_name_plural = verbose_name


class TagType(models.Model):
    # 标签类型
    tag_type = models.CharField(max_length=5)

    def __str__(self):
        return self.tag_type

    class Meta:
        db_table = 'tb_public_offering_tag_type'
        verbose_name = '公开招募标签类别管理'
        verbose_name_plural = verbose_name


class Tag(models.Model):
    # 标签
    tag = models.CharField(max_length=10)
    # 外部键
    tag_type = models.ForeignKey(TagType, on_delete=models.CASCADE)
    # 干员标签
    agent_tags = models.ManyToManyField(to='PublicOffering', through='AgentAndTag')

    def __str__(self):
        return self.tag

    class Meta:
        db_table = 'tb_public_offering_tag'
        verbose_name = '公开招募标签管理'
        verbose_name_plural = verbose_name


class AgentAndTag(models.Model):
    # 干员
    agent_id = models.ForeignKey(PublicOffering, on_delete=models.CASCADE)
    # 标签
    tag_id = models.ForeignKey(Tag, on_delete=models.CASCADE)
