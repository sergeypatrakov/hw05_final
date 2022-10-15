import shutil
import tempfile
from urllib import response

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostContextTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
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
            content_type='image.gif',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
            group=cls.group,
            image=uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)
        cache.clear()

    def check_data(self, response, is_post=False):
        if is_post:
            first_object = response.context.get('post')
        else:
            first_object = response.context.get('page_obj')[0]
        self.assertEqual(first_object.pub_date, self.post.pub_date)
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.group, self.post.group)
        self.assertEqual(first_object.image, self.post.image)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.author_client.get(reverse('posts:index'))
        return self.check_data(response)

    def test_group_posts_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(
            'posts:group_list',
            args=(self.group.slug,),
        ))
        group_from_context = response.context.get('group')
        self.assertEqual(group_from_context, self.post.group)
        return self.check_data(response)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(
            'posts:profile',
            args=(self.author.username,),
        ))
        author_from_context = response.context.get('author')
        self.assertEqual(author_from_context, self.post.author)
        return self.check_data(response)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.author_client.get(reverse(
            'posts:post_detail',
            args=(self.post.id,),
        ))
        return self.check_data(response, is_post=True)

    def test_post_not_used_uncorrect_group(self):
        """Пост не попал не в ту группу."""
        new_group = Group.objects.create(
            title='Тестовый измененный заголовок',
            slug='test-slug-fixed',
            description='Тестовое измененное описание',
        )
        response = self.author_client.get(reverse(
            'posts:group_list',
            args=(new_group.slug,),
        ))
        page_obj = response.context.get('page_obj')
        page_obj_count = len(page_obj)
        self.assertEqual(page_obj_count, 0)
        post_have_group = self.post.group
        self.assertTrue(post_have_group)
        self.assertEqual(
            self.group.posts.first(),
            post_have_group.posts.first(),
        )

    def test_cache_index_work_great(self):
        """Проверяем, что кэш index работает нормально."""
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.author,
        )
        add_content = self.author_client.get(
            reverse('posts:index')
        ).content
        post.delete()
        delete_content = self.author_client.get(
            reverse('posts:index')
        ).content
        self.assertEqual(add_content, delete_content)
        cache.clear()
        cache_clear = self.author_client.get(
            reverse('posts:index')
        ).content
        self.assertNotEqual(add_content, cache_clear)


class PaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post_list = []
        for pryanik in range(settings.TEST_POSTS):
            cls.post_list.append(Post(
                author=cls.author,
                text='Тестовый текст ' + str(pryanik),
                group=cls.group,
            ))
        cls.post = Post.objects.bulk_create(cls.post_list)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.author)

    def test_paginator_contains(self):
        """Проверяемм работу паджинатора."""
        pages = (
            reverse('posts:index'),
            reverse('posts:group_list', args=(self.group.slug,)),
            reverse('posts:profile', args=(self.author.username,)),
        )
        data = (
            ('?page=1', settings.NUMBER_OBJECTS),
            ('?page=2', settings.TEST_PAGINATOR),
        )
        for page in pages:
            with self.subTest(page=page):
                for url, number_posts in data:
                    response = self.author_client.get(page + url)
                    context = response.context.get('page_obj')
                    self.assertEqual(len(context), number_posts)


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(
            username='author_post'
        )
        cls.follower = User.objects.create(
            username='follower_post'
        )
        cls.post = Post.objects.create(
            text='Follow me',
            author=cls.author,
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.follower)
        self.follower_client = Client()
        self.follower_client.force_login(self.author)
    
    def test_follow(self):
        """Проверяем, что автор может подписаться."""
        follow_count = Follow.objects.count()
        self.author_client.post(
            reverse(
                'posts:profile_follow',
                args=(self.author.username,),
            )
        )
        follow = Follow.objects.all().first()
        self.assertEqual(Follow.objects.count(), follow_count + 1)

    def test_unfollow(self):
        """Проверяем, что автор может отписаться."""
        self.author_client.post(
            reverse(
                'posts:profile_follow',
                args=(self.author.username,),
            )
        )
        follow_count = Follow.objects.count()
        self.author_client.post(
            reverse(
                'posts:profile_unfollow',
                args=(self.author.username,),
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_new_post_add_in_followers(self):
        """Новая запись появляется у подписчиков."""
        post = Post.objects.create(
            author=self.author,
            text='Тестовый текст подписки',
        )
        Follow.objects.create(
            user=self.follower,
            author=self.author,
        )
        response = self.author_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(post, response.context['page_obj'])
    
    def test_new_post_no_add_in_followers(self):
        """Новая запись не появляется у тех, кто не подписан."""
        post = Post.objects.create(
            author=self.author,
            text='Тестовый текст подписки',
        )
        response = self.author_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(post, response.context['page_obj'])
