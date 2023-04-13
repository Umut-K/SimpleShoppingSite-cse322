# Generated by Django 4.0.3 on 2023-04-13 07:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='author',
            name='books',
            field=models.ManyToManyField(to='library.book'),
        ),
        migrations.AddField(
            model_name='book',
            name='publisher',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='library.publisher'),
        ),
    ]
