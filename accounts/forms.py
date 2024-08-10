from django import forms
from .models import Account

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder':"Enter the password"
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder':"confirm password"
    }))
    class Meta:
        model = Account
        fields = ['first_name','last_name','phone_number','email','password']
    
    def clean(self):
        cleaned_data = super(RegistrationForm,self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password != confirm_password:
            raise forms.ValidationError(
                "Password does not match!"
            )
    def __init__(self,*args,**kwargs):
        super(RegistrationForm,self).__init__(*args,**kwargs)
        self.fields['first_name'].widget.attrs['placeholder'] = "Enter the first name"
        self.fields['last_name'].widget.attrs['placeholder'] = "Enter the last name"
        self.fields['email'].widget.attrs['placeholder'] = "Enter the email"
        self.fields['phone_number'].widget.attrs['placeholder'] = "Enter the phone number"
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
