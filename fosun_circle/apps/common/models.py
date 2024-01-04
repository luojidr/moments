from django.db import models
from django import forms
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.template.defaultfilters import slugify
from django.utils.timezone import now

# Create your models here.


# #################### test Models ####################
# class AuthorManager(models.Manager):
#     def get_queryset(self):
#         return super().get_queryset().filter(role='A')
#
#
# class Article(models.Model):
#
#     STATUS_CHOICES = (
#         ('d', '草稿'),
#         ('p', '发表'),
#     )
#
#     title = models.CharField('标题', max_length=200, unique=True)
#     slug = models.SlugField('slug', max_length=60)
#     body = models.TextField('正文')
#     pub_date = models.DateTimeField('发布时间', default=now, null=True)
#     create_date = models.DateTimeField('创建时间', auto_now_add=True)
#     mod_date = models.DateTimeField('修改时间', auto_now=True)
#     status = models.CharField('文章状态', max_length=1, choices=STATUS_CHOICES, default='p')
#     views = models.PositiveIntegerField('浏览量', default=0)
#     author = models.ForeignKey(CircleUsersModel, verbose_name='作者', on_delete=models.CASCADE)
#
#     tags = models.ManyToManyField('Tag', verbose_name='标签集合', blank=True)
#
#     def __str__(self):
#         return "<%s: %s>" % (self.id, self.title)
#
#     class Meta:
#         db_table = "test_articles"
#         ordering = ['-pub_date']
#         verbose_name = "article"
#
#     def save(self, *args, **kwargs):
#         if not self.slug or not self.id:
#             self.slug = slugify(self.title)
#         super().save(*args, **kwargs)
#
#     # 定义绝对路径
#     def get_absolute_url(self):
#         return reverse('product_details', kwargs={'pk': self.id})



