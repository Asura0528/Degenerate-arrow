import re

from django.contrib.auth import login
from django.db import DatabaseError
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.urls import reverse
from django_redis import get_redis_connection

from home.models import ArticleCategory, Article, CarouselImg, Comment, PublicOffering, Tag, TagType, AgentAndTag
from django.http import HttpResponseNotFound
from django.core.paginator import Paginator, EmptyPage


# Create your views here.
from users.models import User
from users.views import ForgetView, LoginView


class IndexView(View):
    """
    首页视图
    方法：
        get
    """

    @staticmethod
    def get(request):
        context = {
            'carousel_img': CarouselImg.carousel_img.url
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


class BlogView(View):
    @staticmethod
    def get(request):
        """提供首页广告界面"""
        # 接受参数
        mobile = request.GET.get('mobile')

        if mobile is not None:
            response = ForgetView().post(request)
            return response
        # ?cat_id=xxx&page_num=xxx&page_size=xxx
        cat_id = request.GET.get('cat_id', 1)
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 3)
        # 判断分类id
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseNotFound('没有此分类')

        # 获取博客分类信息
        categories = ArticleCategory.objects.all()

        # 分页数据
        articles = Article.objects.filter(
            category=category
        )

        # 创建分页器：每页N条记录
        paginator = Paginator(articles, page_size)
        # 获取每页商品数据
        try:
            page_articles = paginator.page(page_num)
        except EmptyPage:
            # 如果没有分页数据，默认给用户404
            return HttpResponseNotFound('empty page')
        # 获取列表页总页数
        total_page = paginator.num_pages

        # noinspection PyBroadException
        try:
            is_login = request.COOKIES['is_login']

            if is_login:
                user = request.user
                # 组织模板渲染数据
                context = {
                    'username': user.username,
                    'avatar': user.avatar.url if user.avatar else None,
                    'user_desc': user.user_desc,
                    'categories': categories,
                    'category': category,
                    'articles': page_articles,
                    'page_size': page_size,
                    'total_page': total_page,
                    'page_num': page_num,
                }
                return render(request, 'blog.html', context=context)
        except Exception:
            context = {
                'categories': categories,
                'category': category,
                'articles': page_articles,
                'page_size': page_size,
                'total_page': total_page,
                'page_num': page_num,
            }
            return render(request, 'blog.html', context=context)
        return render(request, 'blog.html')

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
        response.set_cookie('username', user.username, max_age=30 * 24 * 3600)

        return response


class DetailView(View):
    @staticmethod
    def get(request):
        # 接受参数
        mobile = request.GET.get('mobile')

        if mobile is not None:
            response = ForgetView().post(request)
            return response
        # detail/?id=xxx&page_num=xxx&page_size=xxx
        # 获取文档id
        id = request.GET.get('id')
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 5)

        # 获取博客分类信息
        categories = ArticleCategory.objects.all()

        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            messages.info(request, 'empty page')
            return HttpResponseRedirect(reverse('home:detail'))
        else:
            article.total_views += 1
            article.save()

        # 获取当前文章的评论数据
        comments = Comment.objects.filter(
            article=article
        ).order_by('-created')
        # 获取评论总数
        total_count = comments.count()

        # 创建分页器：每页N条记录
        paginator = Paginator(comments, page_size)
        # 获取每页评论数据
        try:
            page_comments = paginator.page(page_num)
        except EmptyPage:
            # 如果page_num不正确，默认给用户404
            messages.info(request, 'empty page')
            return HttpResponseRedirect(reverse('home:detail'))
        # 获取列表页总页数
        total_page = paginator.num_pages

        # noinspection PyBroadException
        try:
            is_login = request.COOKIES['is_login']

            if is_login:
                user = request.user
                # 组织模板渲染数据
                context = {
                    'username': user.username,
                    'avatar': user.avatar.url if user.avatar else None,
                    'user_desc': user.user_desc,
                    'categories': categories,
                    'category': article.category,
                    'article': article,
                    'total_count': total_count,
                    'comments': page_comments,
                    'page_size': page_size,
                    'total_page': total_page,
                    'page_num': page_num,
                }
                return render(request, 'detail.html', context=context)
        except Exception:
            context = {
                'categories': categories,
                'category': article.category,
                'article': article,
                'total_count': total_count,
                'comments': page_comments,
                'page_size': page_size,
                'total_page': total_page,
                'page_num': page_num,
            }
            return render(request, 'detail.html', context=context)
        return render(request, 'detail.html')

    @staticmethod
    def post(request):
        user = request.user

        if user and user.is_authenticated:
            # 接收数据
            id = request.POST.get('id')
            content = request.POST.get('content')

            # 判断文章是否存在
            try:
                article = Article.objects.get(id=id)
            except Article.DoesNotExist:
                messages.info(request, '没有此文章')
                return redirect(reverse('home:blog'))

            # 数据入库
            Comment.objects.create(
                content=content,
                article=article,
                user=user
            )
            # 修改文章评论数量
            article.comments_count += 1
            article.save()
            # 拼接跳转路由
            path = reverse('home:detail') + '?id={}'.format(article.id)
            return redirect(path)

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
        response.set_cookie('username', user.username, max_age=30 * 24 * 3600)

        return response


class ToolView(View):
    @staticmethod
    def get(request):
        # 接受参数
        mobile = request.GET.get('mobile')
        cat_id = request.GET.get('cat_id', 1)
        categories = ArticleCategory.objects.all()

        # noinspection PyBroadException
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except Exception:
            messages.info(request, '没有此分类信息')
            return HttpResponseRedirect(reverse('home:tool'))

        if mobile is not None:
            response = ForgetView().post(request)
            return response

        context = {
            'categories': categories,
            'category': category,
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
                }
                context.update(context_update)
                return render(request, 'tool.html', context=context)
        except Exception:
            return render(request, 'tool.html', context=context)
        return render(request, 'tool.html')

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
            return HttpResponseRedirect(reverse('home:tool'))
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            messages.info(request, '请输入正确手机号')
            return HttpResponseRedirect(reverse('home:tool'))
        # 判断密码是否为8-20位
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            messages.info(request, '请输入8-20位的密码')
            return HttpResponseRedirect(reverse('home:tool'))
        # 判断两次密码是否一致
        if password != password2:
            messages.info(request, '两次输入的密码不一致')
            return HttpResponseRedirect(reverse('home:tool'))

        # 验证短信验证码
        redis_conn = get_redis_connection('default')
        sms_code_server = redis_conn.get('sms:%s' % mobile)
        if sms_code_server is None:
            messages.info(request, '短信验证码已过期')
            return HttpResponseRedirect(reverse('home:tool'))
        if smscode != sms_code_server.decode():
            messages.info(request, '短信验证码错误')
            return HttpResponseRedirect(reverse('home:tool'))

        try:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        except DatabaseError:
            # 如果该手机号不存在，则提醒用户
            messages.info(request, '注册失败，账户已存在')
            return HttpResponseRedirect(reverse('home:tool'))

        # 实现状态保持
        login(request, user)

        # 跳转到首页
        response = redirect(reverse('home:tool'))
        # 设置cookie
        # 登录状态，会话结束后自动过期
        response.set_cookie('is_login', True)
        # 设置用户名有效期一个月
        response.set_cookie('username', user.username, max_age=30 * 24 * 3600)

        return response


class ToolDetailView(View):
    @staticmethod
    def get(request):
        # 接受参数
        mobile = request.GET.get('mobile')
        cat_id = request.GET.get('cat_id', 1)
        categories = ArticleCategory.objects.all()
        tag_type = TagType.objects.all()
        tag = Tag.objects.all()
        agents = PublicOffering.objects.all()
        agents_tags = AgentAndTag.objects.all()

        # noinspection PyBroadException
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except Exception:
            messages.info(request, '没有此分类信息')
            return HttpResponseRedirect(reverse('home:tool_detail'))

        if mobile is not None:
            response = ForgetView().post(request)
            return response

        # noinspection PyBroadException
        try:
            tag_jq = request.GET.get('tag_jq')
            print(tag_jq)
            context = {
                'tag_jq': tag_jq,
                'tag_type': tag_type,
                'tag': tag,
                'agents': agents,
                'categories': categories,
                'category': category,
                'agents_tags': agents_tags,
            }
            return render(request, 'tool_detail.html', context=context)
        except Exception:
            context = {
                'tag_type': tag_type,
                'tag': tag,
                'agents': agents,
                'categories': categories,
                'category': category,
                'agents_tags': agents_tags,
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
                }
                context.update(context_update)
                return render(request, 'tool_detail.html', context=context)
        except Exception:
            return render(request, 'tool_detail.html', context=context)

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
            return HttpResponseRedirect(reverse('home:tool_detail'))
        # 判断手机号是否合法
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            messages.info(request, '请输入正确手机号')
            return HttpResponseRedirect(reverse('home:tool_detail'))
        # 判断密码是否为8-20位
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            messages.info(request, '请输入8-20位的密码')
            return HttpResponseRedirect(reverse('home:tool_detail'))
        # 判断两次密码是否一致
        if password != password2:
            messages.info(request, '两次输入的密码不一致')
            return HttpResponseRedirect(reverse('home:tool_detail'))

        # 验证短信验证码
        redis_conn = get_redis_connection('default')
        sms_code_server = redis_conn.get('sms:%s' % mobile)
        if sms_code_server is None:
            messages.info(request, '短信验证码已过期')
            return HttpResponseRedirect(reverse('home:tool_detail'))
        if smscode != sms_code_server.decode():
            messages.info(request, '短信验证码错误')
            return HttpResponseRedirect(reverse('home:tool_detail'))

        try:
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)
        except DatabaseError:
            # 如果该手机号不存在，则提醒用户
            messages.info(request, '注册失败，账户已存在')
            return HttpResponseRedirect(reverse('home:tool_detail'))

        # 实现状态保持
        login(request, user)

        # 跳转到首页
        response = redirect(reverse('home:tool_detail'))
        # 设置cookie
        # 登录状态，会话结束后自动过期
        response.set_cookie('is_login', True)
        # 设置用户名有效期一个月
        response.set_cookie('username', user.username, max_age=30 * 24 * 3600)

        return response

# class AjaxDealView(View):
#     @staticmethod
#     def ajax_get(request):
#         data = request.GET.get('data')
#         print(data)
#         return HttpResponse(data)
