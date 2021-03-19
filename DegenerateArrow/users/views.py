from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from home.models import ArticleCategory, Article, CarouselImg
from static.lib.captcha.captcha import captcha
from django_redis import get_redis_connection
from utils.response_code import RETCODE
from random import randint
from static.lib.yuntongxun.sms import CCP
from users.models import User
from django.db import DatabaseError
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
import logging
import re

# Create your views here.
# 日志文件
logger = logging.getLogger('django')


# 图片验证码视图
class ImageCodeView(View):
    """
    图片验证码视图
    """
    @staticmethod
    def get(request):
        """
        用于获取请求图片验证码的方法
        :param request:class
        :return:httpResponse
        """
        # 获取前端传递过来的参数
        uuid = request.GET.get('uuid')
        # 判断参数是否为None
        if uuid is None:
            messages.info(request, '请求参数错误')
            return HttpResponseRedirect(reverse('home:index'))
        # 获取验证码内容和验证码图片二进制数据
        text, image = captcha.generate_captcha()
        # 将图片验证码内容保存到redis中，并设置过期时间
        redis_conn = get_redis_connection('default')
        redis_conn.setex('img:%s' % uuid, 300, text)
        # 返回响应，将生成的图片以content_type为image/jpeg的形式返回给请求
        return HttpResponse(image, content_type='image/jpeg')


class SmsCodeView(View):
    """
    短信验证码视图
    """
    @staticmethod
    def get(request):
        """
        用于获取请求短信验证码的方法
        :param request:class
        :return:JsonResponse
        """
        # 接收参数
        image_code_client = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        mobile = request.GET.get('mobile')

        # 校验参数
        if not all([image_code_client, uuid, mobile]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': '缺少必传参数'})

        # 创建连接到redis的对象
        redis_conn = get_redis_connection('default')

        # 提取短信验证码
        image_code_server = redis_conn.get('img:%s' % uuid)
        if image_code_server is None:
            # 图片验证码过期或者不存在
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图形验证码失效'})

        # 删除图片验证码，避免恶意测试图片验证码
        # noinspection PyBroadException
        try:
            redis_conn.delete('img:%s' % uuid)
        except Exception as e:
            logger.error(e)

        # 对比图片验证码
        image_code_server = image_code_server.decode()  # bytes转字符串
        if image_code_client.lower() != image_code_server.lower():  # 转小写后比较
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '输入图形验证码有误'})

        # 生成短信验证码：生成6位数验证码
        sms_code = '%06d' % randint(0, 999999)
        # 将验证码输出在控制台，方便调试
        logger.info(sms_code)
        # 保存短信验证码到redis中，并设置有效期
        redis_conn.setex('sms:%s' % mobile, 300, sms_code)
        # 发送短信验证码
        CCP().send_template_sms(mobile, [sms_code, 5], 1)

        # 响应结果
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '发送短信成功'})


# 登录视图
class LoginView(View):
    @staticmethod
    def get(request):
        # 接受参数
        # noinspection PyBroadException
        try:
            is_login = request.COOKIES['is_login']
            if is_login:
                user = request.user
                # 组织模板渲染数据
                context = {
                    'username': user.username,
                    'avatar': user.avatar.url if user.avatar else None,
                    'user_desc': user.user_desc
                }
                return render(request, 'index.html', context=context)
        except Exception:
            return render(request, 'index.html')
        return render(request, 'index.html')

    @staticmethod
    def post(request):
        # 获取参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        # 检查参数是否齐全
        if not all([mobile, password]):
            messages.info(request, '登录失败，请完成填写')
            return HttpResponseRedirect(reverse('home:index'))

        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            messages.info(request, '请输入正确手机号')
            return HttpResponseRedirect(reverse('home:index'))

        # 判断密码是否为8-20位
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            messages.info(request, '请输入8-20位的密码')
            return HttpResponseRedirect(reverse('home:index'))

        # 认证登录用户
        # 认证字段已在User模型中修改，USERNAME_FILE = 'mobile'
        user = authenticate(mobile=mobile, password=password)

        if user is None:
            messages.info(request, '用户名或密码错误')
            return HttpResponseRedirect(reverse('home:index'))

        # 实现状态保持
        login(request, user)

        # 响应登录结果
        response = redirect(reverse('home:index'))

        # 设置状态保持周期
        if remember != 'on':
            # 没有记住用户，会话结束就过期
            request.session.set_expiry(0)
            # 设置cookie
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=30 * 24 * 3600)
        else:
            # 记住用户，None表示两周后过期
            request.session.set_expiry(None)
            # 设置cookie
            response.set_cookie('is_login', True, max_age=14 * 24 * 3600)
            response.set_cookie('username', user.username, max_age=30 * 24 * 3600)

        return response


# 登出视图
class LogoutView(View):
    @staticmethod
    def get(request):
        # 清理session
        logout(request)
        # 退出登录，重定向到首页
        response = redirect(reverse('home:index'))
        # 退出登录时，清除cookie
        response.delete_cookie('is_login')
        return response


# 注册视图
class RegisterView(View):
    @staticmethod
    def get(request):
        # 接受参数
        mobile = request.GET.get('mobile')
        cat_id = request.GET.get('cat_id', 1)
        categories = ArticleCategory.objects.all()
        hot_articles = Article.recommend
        # noinspection PyBroadException
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except Exception:
            messages.info(request, '没有此分类信息')
            return HttpResponseRedirect(reverse('home:index'))

        # articles = Article.objects.filter(
        #     category=category
        # )
        articles = Article.objects.all()

        if mobile is not None:
            response = ForgetView().post(request)
            return response

        carousel = CarouselImg.objects.all()

        context = {
            'carousel': carousel,
            'categories': categories,
            'category': category,
            'hot_article': hot_articles,
            'articles': articles
        }
        # noinspection PyBroadException
        try:
            is_login = request.COOKIES['is_login']

            if is_login:
                user = request.user
                # 组织模板渲染数据
                context_update = {
                    'username': user.username,
                    'avatar': user.avatar.url if user.avatar else None,
                    'user_desc': user.user_desc,
                }
                context.update(context_update)
                return render(request, 'index.html', context=context)
        except Exception:
            return render(request, 'index.html', context=context)
        return render(request, 'index.html')

    @staticmethod
    def post(request):
        # 获取参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')

        # 如果不存在手机验证码则进入到登录视图
        if smscode is None:
            response = LoginView().post(request)
            return response

        # 判断参数是否齐全
        if not all([mobile, password, password2, smscode]):
            messages.info(request, '注册失败，请完成填写')
            return HttpResponseRedirect(reverse('home:index'))
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            messages.info(request, '请输入正确手机号')
            return HttpResponseRedirect(reverse('home:index'))
        # 判断密码是否为8-20位
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            messages.info(request, '请输入8-20位的密码')
            return HttpResponseRedirect(reverse('home:index'))
        # 判断两次密码是否一致
        if password != password2:
            messages.info(request, '两次输入的密码不一致')
            return HttpResponseRedirect(reverse('home:index'))

        # 验证短信验证码
        redis_conn = get_redis_connection('default')
        sms_code_server = redis_conn.get('sms:%s' % mobile)
        if sms_code_server is None:
            messages.info(request, '短信验证码已过期')
            return HttpResponseRedirect(reverse('home:index'))
        if smscode != sms_code_server.decode():
            messages.info(request, '短信验证码错误')
            return HttpResponseRedirect(reverse('home:index'))

        try:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        except DatabaseError:
            # 如果该手机号不存在，则提醒用户
            messages.info(request, '注册失败，账户已存在')
            return HttpResponseRedirect(reverse('home:index'))

        # 实现状态保持
        login(request, user)

        # 跳转到首页
        response = redirect(reverse('home:index'))
        # 设置cookie
        # 登录状态，会话结束后自动过期
        response.set_cookie('is_login', True)
        # 设置用户名有效期一个月
        response.set_cookie('username', user.username, max_age=30*24*3600)

        return response


class ForgetView(View):
    @staticmethod
    def get(request):
        return render(request, 'index.html')

    @staticmethod
    def post(request):
        # 接收参数
        mobile = request.GET.get('mobile')
        password = request.GET.get('password')
        password2 = request.GET.get('password2')
        smscode = request.GET.get('sms_code')

        # 判断参数是否齐全
        if not all([mobile, password, password2, smscode]):
            messages.info(request, '注册失败，请完成填写')
            return HttpResponseRedirect(reverse('home:index'))
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            messages.info(request, '请输入正确手机号')
            return HttpResponseRedirect(reverse('home:index'))
        # 判断密码是否为8-20位
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            messages.info(request, '请输入8-20位的密码')
            return HttpResponseRedirect(reverse('home:index'))
        # 判断两次密码是否一致
        if password != password2:
            messages.info(request, '两次输入的密码不一致')
            return HttpResponseRedirect(reverse('home:index'))

        # 验证短信验证码
        redis_conn = get_redis_connection('default')
        sms_code_server = redis_conn.get('sms:%s' % mobile)
        if sms_code_server is None:
            messages.info(request, '短信验证码已过期')
            return HttpResponseRedirect(reverse('home:index'))
        if smscode != sms_code_server.decode():
            messages.info(request, '短信验证码错误')
            return HttpResponseRedirect(reverse('home:index'))

        # 根据手机号查询数据
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 如果该手机号不存在，则提示
            messages.info(request, '账户不存在')
            return HttpResponseRedirect(reverse('home:index'))
        else:
            # 修改用户密码
            user.set_password(password)
            user.save()

        # 跳转到登录页面
        response = redirect(reverse('home:index'))
        messages.info(request, '修改成功')
        return response


# 个人中心视图
class HomeView(LoginRequiredMixin, View):
    @staticmethod
    def get(request):
        # 获取用户信息
        user = request.user
        # 组织模板渲染数据
        context = {
            'username': user.username,
            'avatar': user.avatar.url if user.avatar else None,
            'user_desc': user.user_desc
        }
        return render(request, 'home.html', context=context)

    @staticmethod
    def post(request):
        user = request.user
        avatar = request.FILES.get('avatar')
        username = request.POST.get('username', user.username)
        user_desc = request.POST.get('desc', user.user_desc)

        # 修改数据库数据
        # noinspection PyBroadException
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            messages.info(request, '更新失败请稍后再试')
            return HttpResponseRedirect(reverse('users:home'))

        # 返回响应
        response = redirect(reverse('users:home'))
        # 更新cookie信息
        response.set_cookie('username', user.username, max_age=30*24*3600)
        return response


# 撰写帖子视图
class WriteView(LoginRequiredMixin, View):
    @staticmethod
    def get(request):
        # 获取用户信息
        user = request.user
        # 获取博客分类信息
        categories = ArticleCategory.objects.all()
        # 组织模板渲染数据
        context = {
            'username': user.username,
            'avatar': user.avatar.url if user.avatar else None,
            'categories': categories
        }
        return render(request, 'write_blog.html', context=context)

    @staticmethod
    def post(request):
        # 接收数据
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        sumary = request.POST.get('sumary')
        content = request.POST.get('content')
        # recommend = request.POST.get('recommend')
        user = request.user

        # 验证数据是否齐全
        if not all([avatar, title, category_id, sumary, content]):
            messages.info(request, '内容不全，发帖失败')
            return HttpResponseRedirect(reverse('users:writeblog'))

        # 判断文章分类id是否正确
        try:
            article_category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            messages.info(request, '没有此分类信息')
            return HttpResponseRedirect(reverse('users:writeblog'))

        # 数据入库
        try:
            Article.objects.create(
                author=user,
                avatar=avatar,
                category=article_category,
                title=title,
                sumary=sumary,
                content=content,
                recommend=False
            )
        except Exception as e:
            logger.error(e)
            messages.info(request, '发布失败，请稍后再试')
            return HttpResponseRedirect(reverse('users:writeblog'))

        # 返回响应，跳转到文章详情页面
        # 暂时先跳转到首页
        return redirect(reverse('home:index'))


# class BlogView(View):
#     @staticmethod
#     def get(request):
#         # 获取所有分类信息
#         categories = ArticleCategory.objects.all()
#
#         # 接收用户点击的分类id
#         cat_id = request.GET.get('cat_id', 1)
#
#         mobile = request.GET.get('mobile')
#         if mobile is not None:
#             response = ForgetView().post(request)
#             return response
#
#         # 判断分类id
#         try:
#             category = ArticleCategory.objects.get(id=cat_id)
#         except ArticleCategory.DoesNotExist:
#             messages.info(request, '没有此分类')
#             return HttpResponseRedirect(reverse('users:blog'))
#
#         try:
#             is_login = request.COOKIES['is_login']
#
#             if is_login:
#                 user = request.user
#                 # 组织模板渲染数据
#                 context = {
#                     'username': user.username,
#                     'avatar': user.avatar.url if user.avatar else None,
#                     'user_desc': user.user_desc,
#                     'categories': categories,
#                     'category': category
#                 }
#                 return render(request, 'blog.html', context=context)
#         except Exception:
#             context = {
#                 'categories': categories,
#                 'category': category
#             }
#             return render(request, 'blog.html', context=context)
#         return render(request, 'blog.html')
#
#     @staticmethod
#     def post(request):
#         # 获取参数
#         mobile = request.POST.get('mobile')
#         password = request.POST.get('password')
#         password2 = request.POST.get('password2')
#         smscode = request.POST.get('sms_code')
#
#         # 如果不存在手机验证码则进入到登录视图
#         if smscode is None:
#             response = LoginView().post(request)
#             return response
#
#         # 判断参数是否齐全
#         if not all([mobile, password, password2, smscode]):
#             messages.info(request, '注册失败，请完成填写')
#             return HttpResponseRedirect(reverse('users:blog'))
#         # 判断手机号是否合法
#         if not re.match(r'^1[3-9]\d{9}$', mobile):
#             messages.info(request, '请输入正确手机号')
#             return HttpResponseRedirect(reverse('users:blog'))
#         # 判断密码是否为8-20位
#         if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
#             messages.info(request, '请输入8-20位的密码')
#             return HttpResponseRedirect(reverse('users:blog'))
#         # 判断两次密码是否一致
#         if password != password2:
#             messages.info(request, '两次输入的密码不一致')
#             return HttpResponseRedirect(reverse('users:blog'))
#
#         # 验证短信验证码
#         redis_conn = get_redis_connection('default')
#         sms_code_server = redis_conn.get('sms:%s' % mobile)
#         if sms_code_server is None:
#             messages.info(request, '短信验证码已过期')
#             return HttpResponseRedirect(reverse('users:blog'))
#         if smscode != sms_code_server.decode():
#             messages.info(request, '短信验证码错误')
#             return HttpResponseRedirect(reverse('users:blog'))
#
#         try:
#             user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
#         except DatabaseError:
#             # 如果该手机号不存在，则提醒用户
#             messages.info(request, '注册失败，账户已存在')
#             return HttpResponseRedirect(reverse('users:blog'))
#
#         # 实现状态保持
#         login(request, user)
#
#         # 跳转到首页
#         response = redirect(reverse('users:blog'))
#         # 设置cookie
#         # 登录状态，会话结束后自动过期
#         response.set_cookie('is_login', True)
#         # 设置用户名有效期一个月
#         response.set_cookie('username', user.username, max_age=30 * 24 * 3600)
#
#         return response
