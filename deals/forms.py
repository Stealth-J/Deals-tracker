from django import forms
from .models import Profile, UserDeal, Deals

class ProfileForm(forms.ModelForm):
    
    class Meta:
        model = Profile
        fields = ['full_name', 'image', 'notifications_enabled', 'alerts_delete']

    def clean_full_name(self):
        full_name = self.cleaned_data['full_name']
        if full_name.startswith('fy'):
            raise forms.ValidationError('Form cannot begin with fy')
        
        return full_name
    

# class AddUserDealForm(forms.)