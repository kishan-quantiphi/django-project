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
            return redirect('/')
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


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False
            }
            userprofile = self.request.user.userprofile
            if userprofile.one_click_purchasing:
                # fetch the users card list
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    # update the context with the default card
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id)
                    customer.sources.create(source=token)

                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                    )
                    customer.sources.create(source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

            amount = int(order.get_total() * 100)

            try:

                if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        customer=userprofile.stripe_customer_id
                    )
                else:
                    # charge once off on the token
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="usd",
                        source=token
                    )

                # create the payment
                payment = Payment()
                payment.stripe_charge_id = charge['id']
                payment.user = self.request.user
                payment.amount = order.get_total()
                payment.save()

                # assign the payment to the order

                order_items = order.items.all()
                order_items.update(ordered=True)
                for item in order_items:
                    item.save()

                order.ordered = True
                order.payment = payment
                order.ref_code = create_ref_code()
                order.save()

                messages.success(self.request, "Your order was successful!")
                return redirect("/")

            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Rate limit error")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                print(e)
                messages.warning(self.request, "Invalid parameters")
                return redirect("/")

            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Not authenticated")
                return redirect("/")

            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.warning(self.request, "Network error")
                return redirect("/")

            except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.warning(
                    self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect("/")

            except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "A serious error occurred. We have been notifed.")
                return redirect("/")

        messages.warning(self.request, "Invalid data received")
        return redirect("/payment/stripe/")


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



def add_to_cart(request, slug):
    if request.user.is_authenticated():
        item = get_object_or_404(Item, slug=slug)
        order_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False
        )
        order_qs = Order.objects.filter(user=request.user, ordered=False)
        if order_qs.exists():
            order = order_qs[0]
            # check if the order item is in the order
            if order.items.filter(item__slug=item.slug).exists():
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


def remove_from_cart(request, slug):
    if request.user.is_authenticated():
        item = get_object_or_404(Item, slug=slug)
        order_qs = Order.objects.filter(
            user=request.user,
            ordered=False
        )
        if order_qs.exists():
            order = order_qs[0]
            # check if the order item is in the order
            if order.items.filter(item__slug=item.slug).exists():
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
                return redirect("core:product", slug=slug)
        else:
            messages.info(request, "You do not have an active order")
            return redirect("core:product", slug=slug)


def remove_single_item_from_cart(request, slug):
    if request.user.is_authenticated():
        item = get_object_or_404(Item, slug=slug)
        order_qs = Order.objects.filter(
            user=request.user,
            ordered=False
        )
        if order_qs.exists():
            order = order_qs[0]
            # check if the order item is in the order
            if order.items.filter(item__slug=item.slug).exists():
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
                return redirect("core:product", slug=slug)
        else:
            messages.info(request, "You do not have an active order")
            return redirect("core:product", slug=slug)





# def edit_product(request)


def add_product(request,slug):
    if request.method == 'GET':
        item = Item.objects.get(slug=slug)
        context={
            'item':item
        }
        return render(request,'addproduct.html',context)
        

def seller(request):
    if request.user.is_authenticated():
        seller = Seller.objects.filter(user=request.user)
        if seller:
            items = Item.objects.filter(seller=seller[0])
            print(items)
            context = {
                'items' : items
            }
            return render(request,"seller.html",context)
        else:
            return redirect('/')





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

#
# def signup(request):
#     return render(request,"signup.html")
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
