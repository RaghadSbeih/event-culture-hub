from django import forms
from .models import User, Profile

class RegistrationForm(forms.ModelForm):
    full_name = forms.CharField(max_length=91, required=True, label='Full Name')
    email = forms.EmailField(max_length=100, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['full_name', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data['full_name'].split()
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.password = self.cleaned_data['password']  # You should hash this in production
        if commit:
            user.save()
            # Optionally create a profile
            Profile.objects.create(
                user=user,
                first_name=full_name[0],
                last_name=' '.join(full_name[1:]) if len(full_name) > 1 else '',
            )
        return user

class LoginForm(forms.Form):
    username = forms.CharField(max_length=50, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True) 