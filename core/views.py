from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm
from .models import *
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout

import random
import string
import stripe
# import boto3

stripe.api_key = settings.STRIPE_SECRET_KEY


# client = boto3.client('sns',region_name="us-east-1")
# def send_sms(PhoneNumber,Message):
#     try:
#         client.publish(
#                 PhoneNumber='+918806418421',
#                 Message='hey hafhhjfhda'
#         )
#         return True
#     except Exception as e:
#         print(e)
#         return False



def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        name = request.POST['name']
        age = request.POST['age']
        email = request.POST['email']
        city = request.POST['city']
        country = request.POST['country']
        pincode = request.POST['pincode']
        role = request.POST['role']
        phonenumber = request.POST['phonenumber']

        user = User.objects.create(username=username,email=email)
        user.set_password(password)
        user.save()

        user_profile = UserProfile.objects.create(user=user,name=name,age=age,email=email,city=city,country=country,pincode=pincode,role=role,phonenumber=phonenumber)
        user_profile.save()
        return redirect('/login')
    else :
        return render(request,"signup.html")

def login_site(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username = username, password = password)
        print(username)
        print(password)
        if user:
            login(request, user)
            up = UserProfile.objects.get(user=user)
            if(up.role == "buyer"):
                return redirect('/')
            else:
                return redirect('/seller')
        else:
            return HttpResponse('invalid')

    else:
        return render(request, 'login.html')

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        flag = True
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            item_list = order.items.all()
            l=[]
            for i in item_list:
                if i.item.quantity <= 0 :
                    flag = False
                    l.append(i.item.title)
            print(flag)
            form = CheckoutForm()
            if flag:

                context = {
                    'form': form,
                    'couponform': CouponForm(),
                    'order': order,
                    'DISPLAY_COUPON_FORM': True
                }

                shipping_address_qs = Address.objects.filter(
                    user=self.request.user,
                    address_type='S',
                    default=True
                )
                if shipping_address_qs.exists():
                    context.update(
                        {'default_shipping_address': shipping_address_qs[0]})

                billing_address_qs = Address.objects.filter(
                    user=self.request.user,
                    address_type='B',
                    default=True
                )
                if billing_address_qs.exists():
                    context.update(
                        {'default_billing_address': billing_address_qs[0]})

                return render(self.request, "checkout.html", context)
            else:
                print(l)
                context={"outofstock" : True, "list" : l}
                return render(self.request, "order_summary.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            item_list = order.items.all()
            for i in item_list:
                it = i.item
                Item.objects.filter(title=i.item.title).update(quantity = it.quantity - i.quantity)

            if form.is_valid():

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the defualt shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the defualt billing address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')
            order.ordered=True
            order.save()
            return redirect('/')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")




class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"



def add_to_cart(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(Item, pk=pk)
        order_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False
        )
        order_qs = Order.objects.filter(user=request.user, ordered=False)
        if order_qs.exists():
            order = order_qs[0]
            # check if the order item is in the order
            if order.items.filter(item__pk=item.pk).exists():
                order_item.quantity += 1
                order_item.save()
                messages.info(request, "This item quantity was updated.")
                return redirect("core:order-summary")
            else:
                order.items.add(order_item)
                messages.info(request, "This item was added to your cart.")
                return redirect("core:order-summary")
        else:
            ordered_date = timezone.now()
            order = Order.objects.create(
                user=request.user, ordered_date=ordered_date)
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")

    else:
        return redirect('/login')


def remove_from_cart(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(Item, pk=pk)
        order_qs = Order.objects.filter(
            user=request.user,
            ordered=False
        )
        if order_qs.exists():
            order = order_qs[0]
            # check if the order item is in the order
            if order.items.filter(item__pk=item.pk).exists():
                order_item = OrderItem.objects.filter(
                    item=item,
                    user=request.user,
                    ordered=False
                )[0]
                order.items.remove(order_item)
                messages.info(request, "This item was removed from your cart.")
                return redirect("core:order-summary")
            else:
                messages.info(request, "This item was not in your cart")
                return redirect("core:product", pk=pk)
        else:
            messages.info(request, "You do not have an active order")
            return redirect("core:product", pk=pk)


    else:
        return redirect('/login')



def remove_single_item_from_cart(request, pk):
    if request.user.is_authenticated:
        item = get_object_or_404(Item, pk=pk)
        order_qs = Order.objects.filter(
            user=request.user,
            ordered=False
        )
        if order_qs.exists():
            order = order_qs[0]
            # check if the order item is in the order
            if order.items.filter(item__pk=item.pk).exists():
                order_item = OrderItem.objects.filter(
                    item=item,
                    user=request.user,
                    ordered=False
                )[0]
                if order_item.quantity > 1:
                    order_item.quantity -= 1
                    order_item.save()
                else:
                    order.items.remove(order_item)
                messages.info(request, "This item quantity was updated.")
                return redirect("core:order-summary")
            else:
                messages.info(request, "This item was not in your cart")
                return redirect("core:product", pk=pk)
        else:
            messages.info(request, "You do not have an active order")
            return redirect("core:product", pk=pk)

    else:
        return redirect('/login')





# def edit_product(request)


def add_product(request,pk):
    if request.method == 'GET':
        item = Item.objects.get(pk=pk)
        context={
            'item':item
        }
        return render(request,'addproduct.html',context)


# def seller(request):
#     if request.user.is_authenticated:
#         seller = Seller.objects.filter(user=request.user)
#         if seller:
#             items = Item.objects.filter(seller=seller[0])
#             print(items)
#             context = {
#                 'items' : items
#             }
#             return render(request,"seller.html",context)
#         else:
#             return redirect('/')

#     else:
#         return redirect('/login')





def shirt(request):
    items = Item.objects.filter(category='S')
    print(items)
    context = {
        "object_list" : items
    }
    return render(request,"shirt.html",context)


def shoes(request):
    items = Item.objects.filter(category='SH')
    print(items)
    context = {
        "object_list" : items
    }
    return render(request,"shoes.html",context)

def electronics(request):
    items = Item.objects.filter(category='E')
    print(items)
    context = {
        "object_list" : items
    }
    return render(request,"electronics.html",context)


def seller(request):
    if request.user.is_authenticated:
        up = UserProfile.objects.get(user=request.user)
        if up.role == "seller":
            items = Item.objects.filter(seller=request.user)
            print(items)
            context = {
                'object_list' : items
            }
            return render(request,"sellerhome.html",context)
        else:
            return redirect("/login")
    else:
        return redirect('/login')



def edit_product(request,pk):
    item = Item.objects.get(pk=pk)
    if request.method == 'GET':
        context={
        'item':item
        }
        return render(request,'editproduct.html',context)

    if request.method == 'POST':
        # item = Item.objects.get(id = request.)
        item.title = request.POST['title']
        item.price = request.POST['price']
        item.category= request.POST['category']
        item.description = request.POST['description']
        item.quantity = request.POST['quantity']
    try:
        if request.FILES.get('image'):
            item.image=request.FILES.get('image')
    except Exception as e:
        print(e)
    item.label = request.POST['label']
    item.save()
    return redirect('/seller')


def delete_product(request,pk):
    item = Item.objects.get(pk=pk).delete()
    return redirect('/seller')


def add_product(request):
    if request.method == 'POST':
        title = request.POST['title']
        price = request.POST['price']
        category= request.POST['category']
        description = request.POST['description']
        quantity = request.POST['quantity']
   
        label = request.POST['label']
        image=request.FILES.get('image')
        item = Item.objects.create(title=title,price=price,category=category,description=description,quantity=quantity,image=image,label=label,seller=request.user)
        item.save()
        return redirect('/seller')

    else:
        return render(request,'addproduct.html')

#
#
# def login(request):
#     return render(request,"login.html")
# @login_required
# def addproduct(request):
#     seller = Seller.objects.filter(user=request.user)
#     if seller:
#         if request.method == 'POST' :
#             title = request.POST['title']
#             price = request.POST['price']
#             category = request.POST['category']
#             label = request.POST['label']
#             slug = request.POST['slug']
#             description = request.POST['description']
