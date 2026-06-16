from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Task


class TaskViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pass12345')
        self.other_user = User.objects.create_user(username='bob', password='pass12345')
        self.task = Task.objects.create(user=self.user, title='Buy milk')
        self.done_task = Task.objects.create(user=self.user, title='Done task', complete=True)
        self.other_task = Task.objects.create(user=self.other_user, title='Private task')

    def test_task_list_requires_login(self):
        response = self.client.get(reverse('task'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_task_list_only_shows_current_user_tasks(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task'))

        self.assertContains(response, self.task.title)
        self.assertContains(response, self.done_task.title)
        self.assertNotContains(response, self.other_task.title)
        self.assertEqual(response.context['count'], 1)

    def test_search_filters_current_user_tasks(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task'), {'search-area': 'milk'})

        self.assertContains(response, self.task.title)
        self.assertNotContains(response, self.done_task.title)
        self.assertEqual(response.context['search_input'], 'milk')
        self.assertEqual(response.context['count'], 1)

    def test_user_cannot_update_another_users_task(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task-update', args=[self.other_task.id]))

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_another_users_task(self):
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('task-delete', args=[self.other_task.id]))

        self.assertEqual(response.status_code, 404)


class RegisterPageTests(TestCase):
    def test_authenticated_user_is_redirected_from_register_page(self):
        User.objects.create_user(username='alice', password='pass12345')
        self.client.login(username='alice', password='pass12345')

        response = self.client.get(reverse('register'))

        self.assertRedirects(response, reverse('task'))
