from django.urls import path
from .views import *

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('product/<pk>/', ItemDetailView.as_view(), name='product'),
    path('add-to-cart/<pk>/', add_to_cart, name='add-to-cart'),
    path('remove-from-cart/<pk>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<pk>/', remove_single_item_from_cart,name='remove-single-item-from-cart'),


    path('seller/', seller),
    path('shirt/', shirt),
    path('shoes/', shoes),
    path('electronics/', electronics),
    path('edit_product/<pk>',edit_product,name='edit_product'),
    path('delete_product/<pk>',delete_product,name='delete_product'),

    #path('addproduct/', addproduct)

    path('login/', login_site),

    path('signup/', signup),
    path('seller/', seller),
    path('add-product/', add_product),
    path('search/', search),

    path('my_order/', my_order),



    #path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    #path('login/', login),
    #path('signup/', signup)
]
