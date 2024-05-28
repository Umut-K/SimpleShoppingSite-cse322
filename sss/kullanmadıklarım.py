# views.py
@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=request.user)
        password_form = PasswordUpdateForm(request.user, request.POST)

        if form.is_valid():
            form.save()  # Save changes to user information
            messages.success(request, 'Profile updated successfully!')
        if password_form.is_valid():
            password_form.save()  # Save password change
            update_session_auth_hash(request, password_form.user)  # Prevents logout
            messages.success(request, 'Password updated successfully!')

        return redirect('profile')  # Redirect back to profile page

    else:
        form = ProfileEditForm(instance=request.user)
        password_form = PasswordUpdateForm(request.user)

    context = {
        'form': form,
        'password_form': password_form,
    }

    return render(request, 'edit_profile.html', context)


from sss.models import Customer, Product, Order, BasketItem, OrderItem, OrderPayment, Address
from django.shortcuts import render, redirect, get_object_or_404
from sss.forms import CustomerForm, ProductForm, OrderForm, BasketAddForm, RegistrationForm, ProfileEditForm, PasswordUpdateForm
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User



def create_customer(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = CustomerForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            name = form.cleaned_data['name']
            c = Customer(name=name)
            # data saved to the DB
            c.save()
            messages = []
            messages.append(c.name + ' saved!')
            # redirect to a confirmation page if successful
            return render(request, "model_saved.html",
                          {"messages": messages, 'redirect': '/sss'})

    # if a GET (or any other method) we'll create a blank form
    else:
        form = CustomerForm()

    return render(request, 'sss_create_customer.html', {'form': form, 'redirect': '/sss'})

def home(request):
    return render(request, "sss_home.html")

def get_customer(request):
    if request.GET:
        customers = Customer.objects.filter(name=request.GET['name_filter'])
        return render(request, "sss_search_customer.html",
                  context={
                      "user": request.META['USER'],
                      "customers": customers}
                  )
    else:
        return render(request, "sss_search_customer.html")

def create_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list')  # Assuming you have a product list page to redirect to
    else:
        form = ProductForm()
    return render(request, 'create_product.html', {'form': form})

def product_list(request):
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products})

def edit_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'edit_product.html', {'form': form})


def basket_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    form = BasketAddForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        if not request.session.session_key:
            request.session.create()
            request.session.save()
        session_key = request.session.session_key

        quantity = cd['quantity']

        # Check if the product is already in the basket
        basket_item, created = BasketItem.objects.get_or_create(
            session_key=session_key,
            product=product,
            defaults={'quantity': quantity}
        )

        # If the basket item was not created, it means it already exists and we just need to update the quantity
        if not created:
            basket_item.quantity += quantity
            basket_item.save()

        # Redirect to basket detail page to see the item added or updated
        return redirect('product_list')
    else:
        # If the form is not valid, perhaps redirect back to product list with a message
        return redirect('product_list')  # Optionally add an error message mechanism

def basket_detail(request):
    session_key = request.session.session_key
    items = BasketItem.objects.filter(session_key=session_key)
    return render(request, 'basket_detail.html', {'basket_items': items})


@transaction.atomic()
def create_order(request):
    session_key = request.session.session_key
    basket_items = BasketItem.objects.filter(session_key=session_key)
    if not basket_items:
        return redirect('basket_detail')  # Redirect back if the basket is empty

    customer, _ = Customer.objects.get_or_create(email="customer@example.com", defaults={"name": "John Doe"})

    try:
        with transaction.atomic():
            # Create an address
            a = Address(postcode=1)
            a.save()

            # Create the order and immediately save it
            order = Order(customer=customer, shippingaddress=a)
            order.save()  # This must be done before adding OrderItems

            # Transfer all items from the basket to the order
            for item in basket_items:
                if item.product.stock >= item.quantity:  # Check if enough stock is available
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        price=item.product.price,
                        quantity=item.quantity
                    )
                    # Reduce stock here
                    item.product.stock -= item.quantity
                    item.product.save()
                else:
                    # Not enough stock to fulfill the order
                    raise IntegrityError(f"Not enough stock for {item.product.name}")

            # Clear the basket after creating the order
            basket_items.delete()


    except IntegrityError as e:

        print(f"Error: {e}")  # or use logging if you are in a production environment

        return render(request, 'basket_detail.html', {

            'basket_items': basket_items,

            'error_message': str(e)

        })

    return render(request, 'order_success.html', {'order': order})

def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'order_success.html', {'order': order})

@require_POST
def clear_basket(request):
    session_key = request.session.session_key
    BasketItem.objects.filter(session_key=session_key).delete()
    return redirect('basket_detail')  # Redirect to the basket page, which should now be empty

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new user
            return redirect('login')  # Redirect to login page or another page
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redirect to the login page after successful registration
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})

@login_required
def profile(request):
    # Fetch the necessary information
    customer = request.user.customer  # Access the customer related to the user
    user_orders = Order.objects.filter(customer=customer).order_by('-id')
    print(user_orders)
    #user_reviews = Review.objects.filter(user=user).order_by('-created_at')

    context = {
        'username': customer.user.username,
        'joined_date': customer.user.date_joined.strftime("%B %d, %Y"),
        'orders': user_orders,
        # Add other information as needed
    }

    return render(request, 'profile.html', context)

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, ('You were logged out successfully'))
    return redirect('home')

# views.py
@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=request.user)
        password_form = PasswordUpdateForm(request.user, request.POST)

        if form.is_valid():
            form.save()  # Save changes to user information
            messages.success(request, 'Profile updated successfully!')
        if password_form.is_valid():
            password_form.save()  # Save password change
            update_session_auth_hash(request, password_form.user)  # Prevents logout
            messages.success(request, 'Password updated successfully!')

        return redirect('profile')  # Redirect back to profile page

    else:
        form = ProfileEditForm(instance=request.user)
        password_form = PasswordUpdateForm(request.user)

    context = {
        'form': form,
        'password_form': password_form,
    }

    return render(request, 'edit_profile.html', context)



def complete_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if request.method == 'POST':
        # Handle final order confirmation here
        # For example, process payment and update order status
        order.status = 'Completed'
        order.save()
        return redirect('order_success', order_id=order.id)

    return render(request, 'complete_order.html', {'order': order})


{% extends 'base.html' %}

{% block content %}
<h1>Create Order</h1>
{% if user.is_authenticated %}
<p>Do you want to proceed with your default address?</p>

<p>Shipping Address: {{ default_address }}</p>
<p>Billing Address: {{ default_address }}</p>

<p>Are you somewhere else?</p>

<form method="post">
    {% csrf_token %}

    <h2>New Address Information</h2>
    <label for="new_shipping_address">New Shipping Address:</label>
    <input type="text" name="new_shipping_address" id="new_shipping_address">
    <label for="new_billing_address">New Billing Address:</label>
    <input type="text" name="new_billing_address" id="new_billing_address">
    <label for="new_city">City:</label>
    <input type="text" name="new_city" id="new_city">
    <label for="new_state">State:</label>
    <input type="text" name="new_state" id="new_state">
    <label for="new_postcode">Postcode:</label>
    <input type="text" name="new_postcode" id="new_postcode">

    <button type="submit">Proceed</button>
</form>
{%else%}
<form method="post">
    {% csrf_token %}

    <h2>New Address Information</h2>
    <label for="new_shipping_address">New Shipping Address:</label>
    <input type="text" name="new_shipping_address" id="guest_shipping_address">
    <label for="new_billing_address">New Billing Address:</label>
    <input type="text" name="new_billing_address" id="guest_billing_address">
    <label for="new_city">City:</label>
    <input type="text" name="new_city" id="guest_city">
    <label for="new_state">State:</label>
    <input type="text" name="new_state" id="guest_state">
    <label for="new_postcode">Postcode:</label>
    <input type="text" name="new_postcode" id="guest_postcode">

    <button type="submit">Proceed</button>
</form>
{%endif%}
{% endblock %}


{% extends 'base.html' %}

{% block content %}
<h1>Create Order</h1>
{% if user.is_authenticated %}
<p>Do you want to proceed with your default address?</p>

<p>Shipping Address: {{ default_address }}</p>
<p>Billing Address: {{ default_address }}</p>

<form method="post">
    {% csrf_token %}

    <label for="new_shipping_address">Default Shipping Address:</label>
    <input type="text" name="default_shipping_address" value= '{{ default_address }}'>
    <label for="new_billing_address">Default Billing Address:</label>
    <input type="text" name="default_billing_address" value= '{{ default_address }}'>

    <button type="submit" onclick="useDefaultAddress()">Use Default Address</button>

    <button type="submit">Proceed with Default Address</button>
</form>

<script>
    function useDefaultAddress() {
        document.querySelector('form').submit();
    }
</script>

<p>Are you somewhere else?</p>

<form method="post">
    {% csrf_token %}

    <h2>New Address Information</h2>
    <label for="new_shipping_address">New Shipping Address:</label>
    <input type="text" name="new_shipping_address" id="new_shipping_address">
    <label for="new_billing_address">New Billing Address:</label>
    <input type="text" name="new_billing_address" id="new_billing_address">
    <label for="new_city">City:</label>
    <input type="text" name="new_city" id="new_city">
    <label for="new_state">State:</label>
    <input type="text" name="new_state" id="new_state">
    <label for="new_postcode">Postcode:</label>
    <input type="text" name="new_postcode" id="new_postcode">

    <button type="submit">Proceed with New Address</button>
</form>


{% else %}
<form method="post">
    {% csrf_token %}

    <h2>New Address Information</h2>
    <label for="new_shipping_address">New Shipping Address:</label>
    <input type="text" name="new_shipping_address" id="guest_shipping_address">
    <label for="new_billing_address">New Billing Address:</label>
    <input type="text" name="new_billing_address" id="guest_billing_address">
    <label for="new_city">City:</label>
    <input type="text" name="new_city" id="guest_city">
    <label for="new_state">State:</label>
    <input type="text" name="new_state" id="guest_state">
    <label for="new_postcode">Postcode:</label>
    <input type="text" name="new_postcode" id="guest_postcode">

    <button type="submit">Proceed</button>
</form>
{% endif %}
{% endblock %}

@transaction.atomic
def create_order(request):
    if request.user.is_authenticated:
        basket_items = BasketItem.objects.filter(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        basket_items = BasketItem.objects.filter(session_key=session_key)

    if not basket_items:
        return redirect('basket_detail')  # Redirect back if the basket is empty

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            if request.user.is_authenticated:
                if form.cleaned_data['new_shipping_address'] and form.cleaned_data['new_postcode']:
                    shipping_address, created = Address.objects.get_or_create(
                        user=request.user,
                        street=form.cleaned_data['new_shipping_address'],
                        city=form.cleaned_data['new_city'],
                        state=form.cleaned_data['new_state'],
                        postcode=form.cleaned_data['new_postcode'],
                        address_type='shipping'
                    )
                else:
                    shipping_address = form.cleaned_data['shipping_address']
                    default_address = request.user.addresses.filter(address_type='default').first()
                    return render(request, 'create_order.html',
                                  {'form': form, 'default_address': default_address, 'error_message': "All address fields must be filled."})

                if form.cleaned_data['new_billing_address'] and form.cleaned_data['new_postcode']:
                    billing_address, created = Address.objects.get_or_create(
                        user=request.user,
                        street=form.cleaned_data['new_billing_address'],
                        city=form.cleaned_data['new_city'],
                        state=form.cleaned_data['new_state'],
                        postcode=form.cleaned_data['new_postcode'],
                        address_type='billing'
                    )
                else:
                    billing_address = form.cleaned_data['billing_address']
                    return render(request, 'create_order.html',
                                  {'form': form, 'error_message': "All address fields must be filled."})
            else:
                if form.cleaned_data['new_shipping_address'] and form.cleaned_data['new_postcode']:
                    shipping_address = Address(
                        street=form.cleaned_data['new_shipping_address'],
                        city=form.cleaned_data['new_city'],
                        state=form.cleaned_data['new_state'],
                        postcode=form.cleaned_data['new_postcode'],
                        address_type='shipping'
                    )
                    shipping_address.save()
                else:
                    # Handle the error or set a default value if necessary
                    return render(request, 'create_order.html', {'form': form, 'error_message': "All address fields must be filled."})

                if form.cleaned_data['new_billing_address'] and form.cleaned_data['new_postcode']:
                    billing_address = Address(
                        street=form.cleaned_data['new_billing_address'],
                        city=form.cleaned_data['new_city'],
                        state=form.cleaned_data['new_state'],
                        postcode=form.cleaned_data['new_postcode'],
                        address_type='billing'
                    )
                    billing_address.save()
                else:
                    # Handle the error or set a default value if necessary
                    return render(request, 'create_order.html', {'form': form, 'error_message': "All address fields must be filled."})

            try:
                with transaction.atomic():
                    order = Order(
                        user=request.user if request.user.is_authenticated else None,
                        shipping_address=shipping_address,
                        billing_address=billing_address
                    )
                    order.save()

                    for item in basket_items:
                        if item.product.stock >= item.quantity:
                            OrderItem.objects.create(
                                order=order,
                                product=item.product,
                                price=item.product.price,
                                quantity=item.quantity
                            )
                            item.product.stock -= item.quantity
                            item.product.save()
                        else:
                            raise IntegrityError(f"Not enough stock for {item.product.name}")

                    basket_items.delete()

            except IntegrityError as e:
                return render(request, 'basket_detail.html', {'basket_items': basket_items, 'error_message': str(e)})

            return redirect('complete_order', order_id=order.id)

    else:
        form = OrderForm(user=request.user)

    return render(request, 'create_order.html', {'form': form})


{% extends 'base.html' %}

{% block content %}
    <h1>Product List</h1>
    <a href="{% url 'basket_detail' %}">View Basket</a>  <!-- Link to view basket -->
    <ul>
        {% for product in products %}
        <li>
            {{ product.name }} - ${{ product.price }}
            <a href="{% url 'edit_product' product.id %}">Edit</a>

            <!-- Add to Basket Form -->
            <form action="{% url 'basket_add' product.id %}" method="post">
                {% csrf_token %}
                <input type="number" name="quantity" value="1" min="1" max="{{ product.stock }}">
                <input type="hidden" name="override" value="false">
                <input type="submit" value="Add to basket">
            </form>
        </li>
        {% endfor %}
    </ul>
{% endblock %}


class OrderForm(forms.ModelForm):
    shipping_address = forms.ModelChoiceField(queryset=Address.objects.none(), required=False)
    billing_address = forms.ModelChoiceField(queryset=Address.objects.none(), required=False)
    new_shipping_address = forms.CharField(max_length=100, required=False)
    new_billing_address = forms.CharField(max_length=100, required=False)
    new_city = forms.CharField(max_length=20, required=False)
    new_state = forms.CharField(max_length=2, required=False)
    new_postcode = forms.CharField(max_length=10, required=False)

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
        new_shipping_address = cleaned_data.get("new_shipping_address")
        new_billing_address = cleaned_data.get("new_billing_address")
        new_city = cleaned_data.get("new_city")
        new_state = cleaned_data.get("new_state")
        new_postcode = cleaned_data.get("new_postcode")

        if new_shipping_address or new_billing_address or new_city or new_state or new_postcode:
            if not (new_shipping_address and new_billing_address and new_city and new_state and new_postcode):
                raise forms.ValidationError("All new address fields must be filled out if any of them are provided.")

        return cleaned_data

{% extends 'base.html' %}

{% block content %}
<h1>Create Order</h1>
{% if user.is_authenticated %}
<p>Do you want to proceed with your default address?</p>

<p>Shipping Address: {{ default_address.street }}, {{ default_address.city }}, {{ default_address.state }}, {{ default_address.postcode }}</p>
<p>Billing Address: {{ default_address.street }}, {{ default_address.city }}, {{ default_address.state }}, {{ default_address.postcode }}</p>

<form method="post">
    {% csrf_token %}
    <input type="hidden" name="form_type" value="default_address_form">

    <label for="new_shipping_address">Shipping Address:</label>
    <input type="text" name="default_shipping_address" value="{{ default_address.street }}">
    <label for="new_shipping_address">Billing Address:</label>
    <input type="text" name="default_billing_address" value="{{ default_address.street }}">
    <label for="new_city">City:</label>
    <input type="text" name="default_city" value="{{ default_address.city }}">
    <label for="new_state">State:</label>
    <input type="text" name="default_state" value="{{ default_address.state }}">
    <label for="new_postcode">Postcode:</label>
    <input type="text" name="default_postcode" value="{{ default_address.postcode }}">
    <button type="submit">Use Default Address</button>
    <button type="submit">Proceed</button>
</form>

<p>Are you somewhere else?</p>

<form method="post">
    {% csrf_token %}
    <input type="hidden" name="form_type" value="new_address_form">

    <h2>New Address Information</h2>
    <label for="new_shipping_address">New Shipping Address:</label>
    <input type="text" name="new_shipping_address" id="new_shipping_address">
    <label for="new_billing_address">New Billing Address:</label>
    <input type="text" name="new_billing_address" id="new_billing_address">
    <label for="new_city">City:</label>
    <input type="text" name="new_city" id="new_city">
    <label for="new_state">State:</label>
    <input type="text" name="new_state" id="new_state">
    <label for="new_postcode">Postcode:</label>
    <input type="text" name="new_postcode" id="new_postcode">

    <button type="submit">Proceed</button>
</form>
{%else%}
<form method="post">
    {% csrf_token %}
    <input type="hidden" name="form_type" value="guest_address_form">

    <h2>Guest Address Information</h2>

    <label for="new_shipping_address">New Shipping Address:</label>
    <input type="text" name="new_shipping_address" id="guest_shipping_address">
    <label for="new_billing_address">New Billing Address:</label>
    <input type="text" name="new_billing_address" id="guest_billing_address">
    <label for="new_city">City:</label>
    <input type="text" name="new_city" id="guest_city">
    <label for="new_state">State:</label>
    <input type="text" name="new_state" id="guest_state">
    <label for="new_postcode">Postcode:</label>
    <input type="text" name="new_postcode" id="guest_postcode">

    <button type="submit">Proceed</button>
</form>
{%endif%}
{% endblock %}

class OrderForm(forms.ModelForm):
    shipping_address = forms.ModelChoiceField(queryset=Address.objects.none(), required=False)
    billing_address = forms.ModelChoiceField(queryset=Address.objects.none(), required=False)
    new_shipping_address = forms.CharField(max_length=100, required=False)
    new_billing_address = forms.CharField(max_length=100, required=False)
    new_street = forms.CharField(max_length=100, required=False)
    new_city = forms.CharField(max_length=20, required=False)
    new_state = forms.CharField(max_length=2, required=False)
    new_postcode = forms.CharField(max_length=10, required=False)

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
        new_shipping_address = cleaned_data.get("new_shipping_address")
        new_billing_address = cleaned_data.get("new_billing_address")
        new_street = cleaned_data.get("new_street")
        new_city = cleaned_data.get("new_city")
        new_state = cleaned_data.get("new_state")
        new_postcode = cleaned_data.get("new_postcode")

        if new_shipping_address or new_billing_address or new_street or new_city or new_state or new_postcode:
            if not (new_shipping_address and new_billing_address and new_street and new_city and new_state and new_postcode):
                raise forms.ValidationError("All new address fields must be filled out if any of them are provided.")

        return cleaned_data


@transaction.atomic
def create_order(request):
    if request.user.is_authenticated:
        basket_items = BasketItem.objects.filter(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        basket_items = BasketItem.objects.filter(session_key=session_key)

    if not basket_items:
        return redirect('basket_detail')  # Redirect back if the basket is empty

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        form = OrderForm(request.POST, user=request.user)

        if form.is_valid():
            if form_type == 'default_address_form':
                return handle_default_address_form(request, form, basket_items)
            elif form_type == 'new_address_form':
                return handle_new_address_form(request, form, basket_items)
            elif form_type == 'guest_address_form':
                return handle_guest_address_form(request, form, basket_items)
        else:
            default_address = request.user.addresses.filter(
                address_type='default').first() if request.user.is_authenticated else None
            return render(request, 'create_order.html', {'form': form, 'default_address': default_address,
                                                         'error_message': "All address fields must be filled."})

    else:
        form = OrderForm(user=request.user)

    default_address = request.user.addresses.filter(
        address_type='default').first() if request.user.is_authenticated else None
    return render(request, 'create_order.html', {'form': form, 'default_address': default_address})


def handle_default_address_form(request, form, basket_items):
    default_address = request.user.addresses.filter(address_type='default').first()
    if not default_address:
        return render(request, 'create_order.html',
                      {'form': form, 'default_address': default_address, 'error_message': "No default address found."})

    return create_order_with_addresses(request, default_address, default_address, basket_items)


def handle_new_address_form(request, form, basket_items):
    shipping_address = create_or_get_address(request.user, form.cleaned_data['new_shipping_address'],
                                             form.cleaned_data['new_city'], form.cleaned_data['new_state'],
                                             form.cleaned_data['new_postcode'], 'shipping')
    billing_address = create_or_get_address(request.user, form.cleaned_data['new_billing_address'],
                                            form.cleaned_data['new_city'], form.cleaned_data['new_state'],
                                            form.cleaned_data['new_postcode'], 'billing')

    if not shipping_address or not billing_address:
        return render(request, 'create_order.html',
                      {'form': form, 'error_message': "All address fields must be filled."})

    return create_order_with_addresses(request, shipping_address, billing_address, basket_items)


def handle_guest_address_form(request, form, basket_items):
    shipping_address = create_address(form.cleaned_data['new_shipping_address'], form.cleaned_data['new_city'],
                                      form.cleaned_data['new_state'], form.cleaned_data['new_postcode'], 'shipping')
    billing_address = create_address(form.cleaned_data['new_billing_address'], form.cleaned_data['new_city'],
                                     form.cleaned_data['new_state'], form.cleaned_data['new_postcode'], 'billing')

    if not shipping_address or not billing_address:
        return render(request, 'create_order.html',
                      {'form': form, 'error_message': "All address fields must be filled."})

    return create_order_with_addresses(request, shipping_address, billing_address, basket_items)


def create_or_get_address(user, street, city, state, postcode, address_type):
    if street and postcode:
        address, created = Address.objects.get_or_create(
            user=user,
            street=street,
            city=city,
            state=state,
            postcode=postcode,
            address_type=address_type
        )
        return address
    return None


def create_address(street, city, state, postcode, address_type):
    if street and postcode:
        address = Address(
            street=street,
            city=city,
            state=state,
            postcode=postcode,
            address_type=address_type
        )
        address.save()
        return address
    return None


def create_order_with_addresses(request, shipping_address, billing_address, basket_items):
    try:
        with transaction.atomic():
            order = Order(
                user=request.user if request.user.is_authenticated else None,
                shipping_address=shipping_address,
                billing_address=billing_address
            )
            order.save()

            for item in basket_items:
                if item.product.stock >= item.quantity:
                    OrderItem.objects.create(
                        order=order,
                        product=item.product,
                        price=item.product.price,
                        quantity=item.quantity
                    )
                    item.product.stock -= item.quantity
                    item.product.save()
                else:
                    raise IntegrityError(f"Not enough stock for {item.product.name}")

            basket_items.delete()

    except IntegrityError as e:
        return render(request, 'basket_detail.html', {'basket_items': basket_items, 'error_message': str(e)})

    return redirect('complete_order', order_id=order.id)
