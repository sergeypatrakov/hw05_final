from django.forms import ModelForm

from posts.models import Comment, Post


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'group': 'Группа',
            'text': 'Текст',
            'image': 'Картинка',
        }
        help_texts = {
            "text": "Обязательное поле!",
            "group": "Необязательное поле!",
            "image": "Добавь, если хочешь!",
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
