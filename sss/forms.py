import django.forms.widgets
from django.forms import ModelForm, Textarea, TextInput, ChoiceField
from sss.models import Product, Order, Address
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User


class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'price', 'stock', 'image']



class AddressForm(ModelForm):
    class Meta:
        model = Address
        fields = ['street', 'city', 'state', 'postcode', 'address_type']

class OrderForm(forms.ModelForm):
    shipping_address = forms.ModelChoiceField(queryset=Address.objects.none(), required=False)
    billing_address = forms.ModelChoiceField(queryset=Address.objects.none(), required=False)
    new_street = forms.CharField(max_length=100, required=False)
    new_city = forms.CharField(max_length=20, required=False)
    new_state = forms.CharField(max_length=2, required=False)
    new_postcode = forms.CharField(max_length=10, required=False)
    separate_billing_address = forms.BooleanField(required=False)
    new_billing_street = forms.CharField(max_length=100, required=False)
    new_billing_city = forms.CharField(max_length=20, required=False)
    new_billing_state = forms.CharField(max_length=2, required=False)
    new_billing_postcode = forms.CharField(max_length=10, required=False)

    class Meta:
        model = Order
        fields = ['shipping_address', 'billing_address']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['shipping_address'].queryset = Address.objects.filter(user=user, address_type='shipping')
            self.fields['billing_address'].queryset = Address.objects.filter(user=user, address_type='billing')
        else:
            self.fields['shipping_address'].widget = forms.HiddenInput()
            self.fields['billing_address'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        new_street = cleaned_data.get("new_street")
        new_city = cleaned_data.get("new_city")
        new_state = cleaned_data.get("new_state")
        new_postcode = cleaned_data.get("new_postcode")
        separate_billing_address = cleaned_data.get("separate_billing_address")
        new_billing_street = cleaned_data.get("new_billing_street")
        new_billing_city = cleaned_data.get("new_billing_city")
        new_billing_state = cleaned_data.get("new_billing_state")
        new_billing_postcode = cleaned_data.get("new_billing_postcode")

        if new_street or new_city or new_state or new_postcode:
            if not (new_street and new_city and new_state and new_postcode):
                raise forms.ValidationError("All new address fields must be filled out if any of them are provided.")

        if separate_billing_address and (new_billing_street or new_billing_city or new_billing_state or new_billing_postcode):
            if not (new_billing_street and new_billing_city and new_billing_state and new_billing_postcode):
                raise forms.ValidationError("All new billing address fields must be filled out if any of them are provided.")

        return cleaned_data



class BasketAddForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1)
    override = forms.BooleanField(required=False, initial=False, widget=forms.HiddenInput)

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    street = forms.CharField(max_length=100, required=True)
    city = forms.CharField(max_length=20, required=True)
    state = forms.CharField(max_length=2, required=True)
    postcode = forms.CharField(max_length=10, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Address.objects.create(
                user=user,
                street=self.cleaned_data['street'],
                city=self.cleaned_data['city'],
                state=self.cleaned_data['state'],
                postcode=self.cleaned_data['postcode'],
                address_type='default'
            )
        return user


class ProfileEditForm(UserChangeForm):
    password = None  # Exclude the password field

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
class PasswordUpdateForm(PasswordChangeForm):
    class Meta:
        model = User
        fields = ['old_password', 'new_password1', 'new_password2']

class UserSearchForm(forms.Form):
    query = forms.CharField(max_length=100, label='Search for users')