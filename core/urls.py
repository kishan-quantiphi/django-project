from django.urls import path
from .views import *

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('product/<slug>/', ItemDetailView.as_view(), name='product'),
    path('add-to-cart/<slug>/', add_to_cart, name='add-to-cart'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),


    path('seller/', seller),
    path('shirt/', shirt),
    path('shoes/', shoes),
    path('electronics/', electronics),
    path('edit_product/<id>',edit_product,name='edit_product'),
    path('delete_product/<id>',delete_product,name='delete_product'),

    #path('addproduct/', addproduct)

    path('login/', login_site),

    path('signup/', signup),
    # path('sellerhome/', sellerhome),
    # path('add-product/', add_product),

    #path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
    #path('login/', login),
    #path('signup/', signup)
]
