import shutil
import tempfile

from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User
from ..forms import PostForm

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.REVERSE_ADDRESS_PROFILE = reverse(
            'posts:profile', args=(self.author.username,)
        )
        self.REVERSE_ADDRESS_CREATE = reverse(
            'posts:post_create'
        )
        self.REVERSE_ADDRESS_EDIT = reverse(
            'posts:post_edit', args=(self.post.id,)
        )
        self.REVERSE_ADDRESS_DETAIL = reverse(
            'posts:post_detail', args=(self.post.id,)
        )
        self.REVERSE_COMMENT = reverse(
            'posts:add_comment', args=(self.post.id,)
        )

    def test_post_create(self):
        """Валидная форма создает запись в Post."""
        Post.objects.all().delete()
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': PostFormTests.group.id,
            'image': uploaded,
        }
        response = self.author_client.post(
            self.REVERSE_ADDRESS_CREATE,
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, self.REVERSE_ADDRESS_PROFILE)
        self.assertEqual(
            Post.objects.count(),
            post_count + 1
        )
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.author)
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.image, 'posts/small.gif')

    def test_post_edit(self):
        """Проверяем, что происходит изменение поста."""
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        new_group = Group.objects.create(
            title='Тестовый измененный заголовок',
            slug='test-slug-fixed',
            description='Тестовое измененное описание',
        )
        form_data = {
            'text': 'Тестовый измененный текст',
            'group': new_group.id,
        }
        response = self.author_client.post(
            self.REVERSE_ADDRESS_EDIT,
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, self.REVERSE_ADDRESS_DETAIL)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.first()
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.author, self.author)
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(Post.objects.count(), 1)
        response = self.author_client.get(
            reverse(
                'posts:group_list',
                args=(self.group.slug,)
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            len(response.context.get('page_obj')), 0
        )

    def test_client_do_not_create_post(self):
        """Проверяем, что аноним не может создать пост."""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
        }
        response = self.client.post(
            self.REVERSE_ADDRESS_CREATE,
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        redirect = reverse(
            'users:login'
        ) + '?next=' + self.REVERSE_ADDRESS_CREATE
        self.assertRedirects(response, redirect)
        self.assertEqual(
            Post.objects.count(),
            post_count,
        )

    def test_authorized_client_add_comment(self):
        """Проверяем, что пользователь добавляет комментарий."""
        comments_count = Comment.objects.count()
        Post.objects.create(
            text='Тестовый текст',
            author=self.post.author,
        )
        form_data = {
            'text': 'Тестовый комментарий',
        }
        self.author_client.post(
            self.REVERSE_COMMENT,
            data=form_data,
            follow=True,
        )
        comment = Comment.objects.first()
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, self.author)
        self.assertEqual(comment.post_id, self.post.id)

    def test_client_do_not_add_comment(self):
        """Проверяем, что аноним не может комментировать запись."""
        comment_count = Comment.objects.count()
        Post.objects.create(
            text='Тестовый текст',
            author=self.post.author,
        )
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.client.post(
            self.REVERSE_COMMENT,
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.count(), comment_count)
        self.assertRedirects(
            response,
            reverse('login') + '?next=' + self.REVERSE_COMMENT)
