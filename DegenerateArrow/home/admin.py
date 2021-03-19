from django.contrib import admin
from home.models import ArticleCategory, Article, CarouselImg, Comment, AgentAndTag, TagType, Tag, PublicOffering


class AgentAndTagInline(admin.TabularInline):
    model = AgentAndTag
    # 设置可显示字段
    fields = ('tag_id',)


class TagInline(admin.TabularInline):
    model = Tag
    # 设置可显示字段
    fields = ('tag',)


class PublicOfferingAdmin(admin.ModelAdmin):
    search_fields = ('agent_name', 'tag__tag')
    inlines = [AgentAndTagInline]


class TagTypeAdmin(admin.ModelAdmin):
    inlines = [TagInline]  # Inline


class TagAdmin(admin.ModelAdmin):
    search_fields = ('tag', 'tag_type__tag_type')


# Register your models here.
admin.site.register(ArticleCategory)
admin.site.register(Article)
admin.site.register(CarouselImg)
admin.site.register(Comment)
admin.site.register(PublicOffering, PublicOfferingAdmin)
admin.site.register(TagType, TagTypeAdmin)
admin.site.register(Tag, TagAdmin)
