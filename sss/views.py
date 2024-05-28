from sss.models import Product, Order, BasketItem, OrderItem, OrderPayment, Address
from django.shortcuts import render, redirect, get_object_or_404
from sss.forms import ProductForm, OrderForm, BasketAddForm, RegistrationForm, ProfileEditForm, PasswordUpdateForm, UserSearchForm
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User

def home(request):
    return render(request, "sss_home.html")

def create_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
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
        session_key = request.session.session_key
        quantity = cd['quantity']

        # Check if the product is already in the basket for the current user
        basket_item, created = BasketItem.objects.get_or_create(
            user=request.user if request.user.is_authenticated else None,
            session_key=session_key if not request.user.is_authenticated else None,
            product=product,
            defaults={'quantity': quantity},
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


def basket_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        basket_item = BasketItem.objects.filter(product=product, user=request.user).first()
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key
        basket_item = BasketItem.objects.filter(product=product, session_key=session_key).first()

    if basket_item:
        basket_item.delete()

    return redirect('basket_detail')


def basket_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity'))
        if request.user.is_authenticated:
            basket_item, created = BasketItem.objects.get_or_create(product=product, user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.save()
                session_key = request.session.session_key
            basket_item, created = BasketItem.objects.get_or_create(product=product, session_key=session_key)

        if quantity > 0:
            basket_item.quantity = quantity
            basket_item.save()
        else:
            basket_item.delete()

    return redirect('basket_detail')


def basket_detail(request):
    if request.user.is_authenticated:
        items = BasketItem.objects.filter(user=request.user)
    else:
        session_key = request.session.session_key
        items = BasketItem.objects.filter(session_key=session_key)
    return render(request, 'basket_detail.html', {'basket_items': items})


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
    new_street = form.cleaned_data['new_street']
    new_city = form.cleaned_data['new_city']
    new_state = form.cleaned_data['new_state']
    new_postcode = form.cleaned_data['new_postcode']
    user_separate_billing_address = form.cleaned_data.get('separate_billing_address', False)

    shipping_address = create_or_get_address(request.user, new_street, new_city, new_state, new_postcode, 'shipping')

    if user_separate_billing_address:
        billing_address = create_or_get_address(request.user, form.cleaned_data['new_billing_street'], form.cleaned_data['new_billing_city'],
                                                form.cleaned_data['new_billing_state'], form.cleaned_data['new_billing_postcode'], 'billing')
    else:
        billing_address = create_or_get_address(request.user, new_street, new_city, new_state, new_postcode, 'billing')

    if not shipping_address or (user_separate_billing_address and not billing_address):
        return render(request, 'create_order.html',
                      {'form': form, 'error_message': "All address fields must be filled."})

    return create_order_with_addresses(request, shipping_address, billing_address, basket_items)


def handle_guest_address_form(request, form, basket_items):
    new_street = form.cleaned_data['new_street']
    new_city = form.cleaned_data['new_city']
    new_state = form.cleaned_data['new_state']
    new_postcode = form.cleaned_data['new_postcode']
    separate_billing_address = form.cleaned_data.get('separate_billing_address', False)

    shipping_address = create_address(new_street, new_city, new_state, new_postcode, 'shipping')

    if separate_billing_address:
        billing_address = create_address(form.cleaned_data['new_billing_street'], form.cleaned_data['new_billing_city'],
                                         form.cleaned_data['new_billing_state'], form.cleaned_data['new_billing_postcode'], 'billing')
    else:
        billing_address = create_address(new_street, new_city, new_state, new_postcode, 'billing')


    if not shipping_address or (separate_billing_address and not billing_address):
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

def order_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'order_success.html', {'order': order})


def complete_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    total_cost = sum(item.price * item.quantity for item in order.items.all())
    if request.method == 'POST':
        # Handle final order confirmation here
        # For example, process payment and update order status
        order.status = 'Completed'
        order.save()
        return redirect('order_success', order_id=order.id)

    return render(request, 'complete_order.html', {'order': order, 'total_cost': total_cost})

@require_POST
def clear_basket(request):
    if request.user.is_authenticated:
        BasketItem.objects.filter(user=request.user).delete()
    else:
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

@login_required
def profile(request):
    user_orders = Order.objects.filter(user=request.user).order_by('-id')
    context = {
        'username': request.user.username,
        'joined_date': request.user.date_joined.strftime("%B %d, %Y"),
        'orders': user_orders,
        # Add other information as needed
    }
    return render(request, 'profile.html', context)

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, ('You were logged out successfully'))
    return redirect('home')

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

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    total_cost = sum(item.price * item.quantity for item in order.items.all())
    return render(request, 'order_detail.html', {'order': order, 'total_cost': total_cost})

def user_search(request):
    form = UserSearchForm()
    results = []

    if request.method == 'GET':
        form = UserSearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = User.objects.filter(username__startswith=query)

    return render(request, 'user_search.html', {'form': form, 'results': results})