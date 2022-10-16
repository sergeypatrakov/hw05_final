from http import HTTPStatus

from django.test import TestCase


class AboutURLTests(TestCase):
    def test_all_about_exist_at_desired_location(self):
        """Проверяем, чтто страницы доступны пользователям."""
        urls = {
            '/about/author/': HTTPStatus.OK,
            '/about/tech/': HTTPStatus.OK,
        }
        for address, code in urls.items():
            with self.subTest(address=address):
                response = self.client.get(address).status_code
                self.assertEqual(response, code)

    def test_all_about_url_uses_correct_template(self):
        """Проверяем работу шаблоны."""
        templates = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }
        for address, template in templates.items():
            with self.subTest(address=address):
                response = self.client.get(address)
                self.assertTemplateUsed(response, template)
