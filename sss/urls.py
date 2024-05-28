from django.urls import path
from sss.views import home, create_product, product_list, edit_product, basket_add, basket_detail, create_order, clear_basket, register, logout_view, profile, edit_profile, complete_order, order_success, order_detail, basket_remove, basket_update, user_search
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    #path('search', get_customer),
    #path('create', create_customer),
    path('user_search/', user_search, name='user_search'),
    path('new-product/', create_product),
    path('products/', product_list, name='product_list'),
    path('edit-product/<int:product_id>/', edit_product, name='edit_product'),
    path('basket-add/<int:product_id>/', basket_add, name='basket_add'),
    path('basket_remove/<int:product_id>/', basket_remove, name='basket_remove'),
    path('basket_update/<int:product_id>/', basket_update, name='basket_update'),
    path('basket/', basket_detail, name='basket_detail'),
    path('create-order/', create_order, name='create_order'),
    path('complete_order/<int:order_id>/', complete_order, name='complete_order'),
    path('order_success/<int:order_id>/', order_success, name='order_success'),
    path('order/<int:order_id>/', order_detail, name='order_detail'),
    path('clear-basket/', clear_basket, name='clear_basket'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('profile/', profile, name='profile'),
    path('profile/edit/', edit_profile, name='edit_profile'),
]