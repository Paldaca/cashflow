from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from BCV.models import ExchangeRateHistory
from organizations.models import Organization
from accounts.models import Profile


class SuperadminUserCreateForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'cf-input', 'placeholder': 'usuario@correo.com'}),
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Nombre'}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Apellido',
        widget=forms.TextInput(attrs={'class': 'cf-input', 'placeholder': 'Apellido'}),
    )
    edit = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        initial='Editor',
        label='Edit (Permisos)',
        widget=forms.Select(attrs={'class': 'cf-select'}),
    )
    is_active = forms.BooleanField(required=False, initial=True, label='Activo')
    is_staff = forms.BooleanField(required=False, initial=False, label='Staff')
    is_superuser = forms.BooleanField(required=False, initial=False, label='Superadministrador')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'password1', 'password2', 'edit', 'is_active', 'is_staff', 'is_superuser',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'cf-input',
            'placeholder': 'nombre_usuario',
        })
        for field in ('password1', 'password2'):
            self.fields[field].widget.attrs.update({
                'class': 'cf-input',
                'placeholder': '********',
            })

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        
        # Guardar el perfil si el usuario ya existe o fue guardado
        if user.pk:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.edit = self.cleaned_data.get('edit')
            profile.save()
            
        return user


class SuperadminUserEditForm(forms.ModelForm):
    new_password = forms.CharField(
        required=False,
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={'class': 'cf-input', 'placeholder': 'Dejar vacío para no cambiar'}),
    )
    new_password_confirm = forms.CharField(
        required=False,
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'cf-input', 'placeholder': 'Repetir contraseña'}),
    )
    edit = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        label='Edit (Permisos)',
        widget=forms.Select(attrs={'class': 'cf-select'}),
    )
    is_active = forms.BooleanField(required=False, label='Activo')
    is_staff = forms.BooleanField(required=False, label='Staff')
    is_superuser = forms.BooleanField(required=False, label='Superadministrador')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'edit', 'is_active', 'is_staff', 'is_superuser')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'cf-input'}),
            'first_name': forms.TextInput(attrs={'class': 'cf-input'}),
            'last_name': forms.TextInput(attrs={'class': 'cf-input'}),
            'email': forms.EmailInput(attrs={'class': 'cf-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            profile, _ = Profile.objects.get_or_create(user=self.instance)
            self.fields['edit'].initial = profile.edit

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('new_password')
        confirm = cleaned.get('new_password_confirm')
        if password or confirm:
            if password != confirm:
                self.add_error('new_password_confirm', 'Las contraseñas no coinciden: verifique que ambos campos contengan exactamente la misma contraseña.')
            else:
                validate_password(password, self.instance)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('new_password')
        if password:
            user.set_password(password)
        
        if commit:
            user.save()
            
        # Guardar el perfil si el usuario ya existe o fue guardado
        if user.pk:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.edit = self.cleaned_data.get('edit')
            profile.save()
            
        return user


class SuperadminOrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'cf-input',
                'placeholder': 'Nombre de la organización',
            }),
        }


class SuperadminOrganizationWizardForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label='Nombre de la organización',
        widget=forms.TextInput(attrs={
            'class': 'cf-input',
            'placeholder': 'Ej. Empresa ABC C.A.',
            'autocomplete': 'organization',
        }),
    )
    org_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_superuser=False, is_active=True).order_by('username'),
        required=False,
        label='Administradores existentes',
    )
    new_user_username = forms.CharField(
        max_length=150,
        required=False,
        label='Usuario',
        widget=forms.TextInput(attrs={'class': 'cf-input cf-input--sm', 'placeholder': 'nombre_usuario'}),
    )
    new_user_email = forms.EmailField(
        required=False,
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'cf-input cf-input--sm', 'placeholder': 'usuario@correo.com'}),
    )
    new_user_first_name = forms.CharField(
        max_length=150,
        required=False,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'cf-input cf-input--sm', 'placeholder': 'Nombre'}),
    )
    new_user_last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Apellido',
        widget=forms.TextInput(attrs={'class': 'cf-input cf-input--sm', 'placeholder': 'Apellido'}),
    )
    new_user_password1 = forms.CharField(
        required=False,
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'cf-input cf-input--sm', 'placeholder': '********'}),
    )
    new_user_password2 = forms.CharField(
        required=False,
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'cf-input cf-input--sm', 'placeholder': '********'}),
    )

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if not name:
            raise ValidationError('El nombre de la organización es obligatorio: ingrese un nombre antes de continuar.')
        if Organization.objects.filter(name__iexact=name).exists():
            raise ValidationError(
                'Ya existe una organización registrada con ese nombre exacto. Utilice un nombre '
                'diferente o edite la organización existente.'
            )
        return name

    def clean(self):
        cleaned_data = super().clean()
        org_users = cleaned_data.get('org_users') or []
        username = (cleaned_data.get('new_user_username') or '').strip()

        for user in org_users:
            if user.is_superuser:
                raise ValidationError(
                    'Los superadministradores no pueden asignarse como administradores de una '
                    'organización: quite la selección de superusuarios de la lista de administradores.'
                )

        if username:
            if User.objects.filter(username__iexact=username).exists():
                self.add_error('new_user_username', 'Ese nombre de usuario ya está en uso por otra cuenta. Elija un nombre de usuario diferente.')
            if not cleaned_data.get('new_user_email'):
                self.add_error('new_user_email', 'Debe indicar un email para el nuevo usuario que está creando.')
            password1 = cleaned_data.get('new_user_password1')
            password2 = cleaned_data.get('new_user_password2')
            if not password1:
                self.add_error('new_user_password1', 'Debe indicar una contraseña para el nuevo usuario.')
            if not password2:
                self.add_error('new_user_password2', 'Debe repetir la contraseña en el campo de confirmación.')
            if password1 and password2 and password1 != password2:
                self.add_error('new_user_password2', 'Las contraseñas no coinciden: verifique que ambos campos contengan exactamente la misma contraseña.')
            elif password1 and password2 and password1 == password2:
                try:
                    validate_password(password1)
                except ValidationError as exc:
                    self.add_error('new_user_password1', exc)

        if not org_users and not username:
            raise ValidationError(
                'Debe asignar al menos un administrador a la organización: seleccione un usuario '
                'existente de la lista o complete los datos para crear uno nuevo.'
            )

        cleaned_data['new_user_username'] = username
        return cleaned_data


class OrganizationAccessForm(forms.Form):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_superuser=False).order_by('username'),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'cf-input', 'size': 8}),
        label='Usuarios con acceso',
    )


class ProjectAccessForm(forms.Form):
    """Usuarios marcados en el modal de accesos de un proyecto.

    Acepta cualquier usuario existente; la vista es la que recorta la selección
    a los miembros elegibles (organización dueña del proyecto y organizaciones
    con las que esté compartido).
    """
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Usuarios con acceso al proyecto',
    )


class BcvRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRateHistory
        fields = ['rate_date', 'currency', 'rate']
        widgets = {
            'rate_date': forms.DateInput(attrs={'class': 'cf-input', 'type': 'date'}),
            'currency': forms.Select(attrs={'class': 'cf-select'}),
            'rate': forms.NumberInput(attrs={
                'class': 'cf-input',
                'step': '0.0001',
                'min': '0.0001',
                'placeholder': '0.0000',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].choices = [
            (ExchangeRateHistory.CURRENCY_USD, 'Dólar (USD)'),
            (ExchangeRateHistory.CURRENCY_EUR, 'Euro (EUR)'),
        ]

    def clean_currency(self):
        currency = self.cleaned_data.get('currency')
        allowed = {ExchangeRateHistory.CURRENCY_USD, ExchangeRateHistory.CURRENCY_EUR}
        if currency not in allowed:
            raise forms.ValidationError('Moneda no permitida: la tasa solo puede registrarse para Dólar (USD) o Euro (EUR).')
        return currency

    def clean_rate(self):
        rate = self.cleaned_data.get('rate')
        if rate is not None and rate <= 0:
            raise forms.ValidationError('La tasa debe ser un valor mayor que cero: ingrese la tasa de cambio vigente.')
        return rate
