# Generated by Django 2.2 on 2021-03-09 20:10

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_comment'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgentAndTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='PublicOffering',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent_name', models.CharField(max_length=5)),
                ('agent_img', models.ImageField(upload_to='agent/thumbnail/%Y%m%d')),
                ('agent_level', models.IntegerField(default=1, validators=[django.core.validators.MaxValueValidator(6), django.core.validators.MinValueValidator(1)])),
            ],
            options={
                'verbose_name': '公开招募干员管理',
                'verbose_name_plural': '公开招募干员管理',
                'db_table': 'tb_public_offering_agent',
            },
        ),
        migrations.CreateModel(
            name='TagType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag_type', models.CharField(max_length=5)),
            ],
            options={
                'verbose_name': '公开招募标签类别管理',
                'verbose_name_plural': '公开招募标签类别管理',
                'db_table': 'tb_public_offering_tag_type',
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag', models.CharField(max_length=10)),
                ('agent_tags', models.ManyToManyField(through='home.AgentAndTag', to='home.PublicOffering')),
                ('tag_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.TagType')),
            ],
            options={
                'verbose_name': '公开招募标签管理',
                'verbose_name_plural': '公开招募标签管理',
                'db_table': 'tb_public_offering_tag',
            },
        ),
        migrations.AddField(
            model_name='agentandtag',
            name='agent_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.PublicOffering'),
        ),
        migrations.AddField(
            model_name='agentandtag',
            name='tag_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='home.Tag'),
        ),
    ]
