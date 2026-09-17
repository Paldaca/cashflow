from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from organizations.models import (
    Account,
    Organization,
    OrganizationAccess,
    Project,
    ProjectOrganizationAccess,
    ProjectUserAccess,
    Transaction,
)


class SuperadminPanelTests(TestCase):
    def setUp(self):
        self.superadmin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='password123',
        )
        self.user = User.objects.create_user(
            username='normal',
            email='normal@test.com',
            password='password123',
        )
        self.client = Client()

    def test_superuser_login_redirects_to_panel(self):
        response = self.client.post(reverse('login'), {
            'username': 'admin',
            'password': 'password123',
        })
        self.assertRedirects(response, reverse('superadmin_dashboard'))

    def test_superuser_blocked_from_org_dashboard(self):
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('superadmin_dashboard'))

    def test_normal_user_cannot_access_superadmin(self):
        self.client.login(username='normal', password='password123')
        response = self.client.get(reverse('superadmin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_usuarios(self):
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('superadmin_usuarios'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'normal')

    def test_superuser_cannot_delete_self(self):
        self.client.login(username='admin', password='password123')
        response = self.client.post(reverse('superadmin_eliminar_usuario', args=[self.superadmin.pk]))
        self.assertRedirects(response, reverse('superadmin_usuarios'))
        self.assertTrue(User.objects.filter(pk=self.superadmin.pk).exists())

    def test_wizard_creates_bs_account(self):
        self.client.login(username='admin', password='password123')
        response = self.client.post(reverse('superadmin_crear_organizacion_wizard'), {
            'name': 'Empresa Test',
            'org_users': [self.user.pk],
            'account_currency': ['BS'],
            'account_name': ['Caja Bs.'],
            'account_balance': ['1000.00'],
        })
        self.assertRedirects(response, reverse('superadmin_organizaciones'))
        org = Organization.objects.get(name='Empresa Test')
        account = Account.objects.get(organization=org)
        self.assertEqual(account.currency, Account.CURRENCY_BS)
        self.assertEqual(account.name, 'Caja Bs.')
        self.assertEqual(Transaction.objects.filter(account=account).count(), 1)
        tx = Transaction.objects.get(account=account)
        self.assertEqual(tx.amount_bs, 1000)
        self.assertGreater(tx.amount_usd, 0)

    def test_wizard_creates_usd_account_separately(self):
        self.client.login(username='admin', password='password123')
        response = self.client.post(reverse('superadmin_crear_organizacion_wizard'), {
            'name': 'Empresa USD',
            'org_users': [self.user.pk],
            'account_currency': ['USD'],
            'account_name': ['Caja USD'],
            'account_balance': ['250.00'],
        })
        self.assertRedirects(response, reverse('superadmin_organizaciones'))
        account = Account.objects.get(organization__name='Empresa USD')
        self.assertEqual(account.currency, Account.CURRENCY_USD)
        tx = Transaction.objects.get(account=account)
        self.assertEqual(tx.real_dollars, 250)
        self.assertEqual(tx.amount_usd, 0)
        self.assertEqual(tx.amount_bs, 0)


class SuperadminProjectAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'a@t.com', 'password123')
        self.org = Organization.objects.create(name='Org A')
        self.other_org = Organization.objects.create(name='Org B')
        self.u1 = User.objects.create_user('uno', 'uno@t.com', 'password123')
        self.u2 = User.objects.create_user('dos', 'dos@t.com', 'password123')
        self.outsider = User.objects.create_user('fuera', 'f@t.com', 'password123')
        OrganizationAccess.objects.create(organization=self.org, user=self.u1)
        OrganizationAccess.objects.create(organization=self.org, user=self.u2)
        OrganizationAccess.objects.create(organization=self.other_org, user=self.outsider)
        self.p1 = Project.objects.create(organization=self.org, name='Proyecto 1')
        self.p2 = Project.objects.create(organization=self.org, name='Proyecto 2')
        self.client.login(username='admin', password='password123')

    def test_page_lists_projects_and_members(self):
        ProjectUserAccess.objects.create(user=self.u1, project=self.p1)
        r = self.client.get(reverse('superadmin_proyectos'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Proyecto 1')
        self.assertContains(r, 'Proyecto 2')
        self.assertContains(r, 'Org A')
        data = r.context['projects_data']
        org_a = [o for o in data if o['name'] == 'Org A'][0]
        self.assertEqual(len(org_a['projects']), 2)
        p1 = [p for p in org_a['projects'] if p['name'] == 'Proyecto 1'][0]
        self.assertEqual(p1['member_ids'], [self.u1.id])
        self.assertEqual({m['id'] for m in p1['eligible']}, {self.u1.id, self.u2.id})

    def test_non_superuser_forbidden(self):
        self.client.logout()
        self.client.login(username='uno', password='password123')
        self.assertEqual(self.client.get(reverse('superadmin_proyectos')).status_code, 403)

    def test_grant_and_revoke_project_access(self):
        ProjectUserAccess.objects.create(user=self.u1, project=self.p1)
        url = reverse('superadmin_accesos_proyecto', args=[self.p1.id])
        r = self.client.post(url, {'users': [self.u2.id]})
        self.assertRedirects(r, reverse('superadmin_proyectos') + f'#org-{self.org.id}',
                             fetch_redirect_response=False)
        self.assertEqual(
            set(ProjectUserAccess.objects.filter(project=self.p1).values_list('user_id', flat=True)),
            {self.u2.id},
        )

    def test_ineligible_user_is_ignored(self):
        url = reverse('superadmin_accesos_proyecto', args=[self.p1.id])
        self.client.post(url, {'users': [self.u1.id, self.outsider.id]})
        self.assertEqual(
            set(ProjectUserAccess.objects.filter(project=self.p1).values_list('user_id', flat=True)),
            {self.u1.id},
        )

    def test_shared_org_user_is_eligible(self):
        ProjectOrganizationAccess.objects.create(project=self.p1, organization=self.other_org)
        url = reverse('superadmin_accesos_proyecto', args=[self.p1.id])
        self.client.post(url, {'users': [self.outsider.id]})
        self.assertTrue(ProjectUserAccess.objects.filter(project=self.p1, user=self.outsider).exists())
        r = self.client.get(reverse('superadmin_proyectos'))
        org_a = [o for o in r.context['projects_data'] if o['name'] == 'Org A'][0]
        p1 = [p for p in org_a['projects'] if p['id'] == self.p1.id][0]
        self.assertEqual(p1['outside_count'], 1)

    def test_matrix_updates_all_pairs(self):
        ProjectUserAccess.objects.create(user=self.u1, project=self.p1)
        url = reverse('superadmin_matriz_accesos_proyectos', args=[self.org.id])
        r = self.client.post(url, {'access': [
            f'{self.p1.id}:{self.u2.id}',
            f'{self.p2.id}:{self.u1.id}',
            f'{self.p2.id}:{self.u2.id}',
            f'{self.p1.id}:{self.outsider.id}',   # no es miembro: se ignora
            'basura',
        ]})
        self.assertRedirects(r, reverse('superadmin_proyectos') + f'#org-{self.org.id}',
                             fetch_redirect_response=False)
        pairs = set(ProjectUserAccess.objects.values_list('project_id', 'user_id'))
        self.assertEqual(pairs, {
            (self.p1.id, self.u2.id),
            (self.p2.id, self.u1.id),
            (self.p2.id, self.u2.id),
        })

    def test_matrix_preserves_shared_org_access(self):
        ProjectOrganizationAccess.objects.create(project=self.p1, organization=self.other_org)
        ProjectUserAccess.objects.create(user=self.outsider, project=self.p1)
        url = reverse('superadmin_matriz_accesos_proyectos', args=[self.org.id])
        self.client.post(url, {'access': [f'{self.p1.id}:{self.u1.id}']})
        self.assertTrue(ProjectUserAccess.objects.filter(project=self.p1, user=self.outsider).exists())
        self.assertTrue(ProjectUserAccess.objects.filter(project=self.p1, user=self.u1).exists())

    def test_get_requests_redirect(self):
        self.assertRedirects(
            self.client.get(reverse('superadmin_accesos_proyecto', args=[self.p1.id])),
            reverse('superadmin_proyectos'), fetch_redirect_response=False)
        self.assertRedirects(
            self.client.get(reverse('superadmin_matriz_accesos_proyectos', args=[self.org.id])),
            reverse('superadmin_proyectos'), fetch_redirect_response=False)

    def test_dashboard_and_org_page_still_work(self):
        self.assertEqual(self.client.get(reverse('superadmin_dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('superadmin_organizaciones')).status_code, 200)
