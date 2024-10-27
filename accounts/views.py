from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from .forms import RegistrationForm, UserForm, UserProfileForm
from .models import Account, UserProfile
from orders.models import Order, OrderProduct
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
#verification email
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from cart.models import Cart,CartItem
from cart.views import _cart_id
import requests



def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split('@')[0]
            user = Account.objects.create_user(first_name=first_name,
                                               last_name=last_name,
                                               email=email,
                                               password=password,
                                               username=username)
            user.phone_number = phone_number
            user.save()

            # Create UserProfile
            profile = UserProfile()
            profile.user_id = user.id
            profile.profile_picture = 'default/default-user.png'
            profile.save()

            # User verification
            current_site = get_current_site(request)
            mail_subject = "Please activate your account"
            message = render_to_string('accounts/account_verification_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user)
            })
            to_email = email
            send_email = EmailMessage(
                mail_subject,
                message,
                to=[to_email]
            )
            send_email.send()

            return redirect('/accounts/login/?command=verification&email='+email)
    else:
        form = RegistrationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'accounts/register.html', context)

# def login(request):
#     if request.method == 'POST':
#         email = request.POST['email']
#         password = request.POST['password']
#         user = auth.authenticate(email=email,password=password)
#         if user is not None:
#             try:
#                 cart = Cart.objects.get(cart_id = _cart_id(request))
#                 Is_cart_item_exist = CartItem.objects.filter(cart = cart).exists()
#                 if Is_cart_item_exist:
#                     cart_item = CartItem.objects.filter(cart = cart)
#                     #Getting the product variation by cart id
#                     product_variation = []
#                     for item in cart_item:
#                         variation = item.variations.all()
#                         product_variation.append(list(variation))
#                     # Get the cart items from the user to access the product variations
#                     cart_item = CartItem.objects.filter(user = user)
#                     ex_var_list = []
#                     id = []
#                     for item in cart_item:
#                         existing_variation = item.variations.all()
#                         ex_var_list.append(list(existing_variation))
#                         id.append(item.id)
                    
#                     for pr in product_variation:
#                         if pr in ex_var_list:
#                             index = ex_var_list.index(pr)
#                             item_id = id[index]
#                             item = CartItem.objects.get(id=item_id)
#                             item.quantity += 1
#                             item.user = user
#                             item.save()
#                         else:
#                             cart_item = CartItem.objects.filter(cart = cart)
#                             for item in cart_item:
#                                 item.user = user
#                                 item.save()
                            
#             except:
#                 pass

#             auth.login(request,user)
#             messages.success(request,"You are now logged in")
#             return redirect('dashboard')
#         else:
#             messages.error(request,"Invalid login credentials.")
#             return redirect('login')

#     return render(request,'accounts/login.html')
def login(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        user = auth.authenticate(email=email, password=password)
        
        if user is not None:
            try:
                # Get the cart for the anonymous user
                cart = Cart.objects.get(cart_id=_cart_id(request))
                cart_items = CartItem.objects.filter(cart=cart)

                # Process cart items from the anonymous cart
                for item in cart_items:
                    product_variation = list(item.variations.all())

                    # Check if the item already exists in the logged-in user's cart
                    existing_cart_item = CartItem.objects.filter(user=user, variations__in=product_variation).first()

                    if existing_cart_item:
                        # Update quantity of the existing item
                        existing_cart_item.quantity += item.quantity
                        existing_cart_item.save()
                    else:
                        # Add new items to the logged-in user's cart
                        item.user = user
                        item.cart = None  # Remove the anonymous cart association
                        item.save()
                
                # Clear the anonymous cart only after merging items
                cart_items.delete()

            except Exception as e:
                print(f"Error: {e}")

            # Log the user in and redirect
            auth.login(request, user)
            messages.success(request, "You are now logged in")
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                print("Query------",query)
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    next_page = params['next']
                    return redirect(next_page)
            except:
                return redirect('dashboard')
        
        else:
            messages.error(request, "Invalid login credentials.")
            return redirect('login')

    return render(request, 'accounts/login.html')


@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request,"Your logged out!")
    return redirect('login')


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account.objects.get(pk=uid)
    except(TypeError,ValueError,OverflowError,Account.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user,token):
        user.is_active = True
        user.save()
        messages.success(request,"Congratulation, you are successfully activated")
        return redirect('login')
    else:
        messages.error("Invalid activation link")
        return redirect('register')
    
def dashboard(request):
    orders = Order.objects.order_by('-created_at').filter(user_id = request.user.id, is_ordered = True)
    order_count = orders.count()
    userprofile = UserProfile.objects.get(user_id=request.user.id)
    context = {
        'orders':orders,
        'order_count':order_count,
        'userprofile':userprofile,
    }
    return render(request,'accounts/dashboard.html',context)

def forgotPassword(request):
    if request.method == 'POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)
            # Reset password email
            current_site = get_current_site(request)
            mail_subject = "Reset your password"
            message = render_to_string('accounts/reset_password_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user)
            })
            to_email = email
            send_email = EmailMessage(
                mail_subject,
                message,
                to=[to_email]
            )
            send_email.send()

            messages.success(request,"Password reset email has been send to your email address")
            return redirect('login')
        else:
            messages.error(request,"Account does not exist")
            return redirect('forgotPassword')

        

    return render(request,'accounts/forgotPassword.html')

def reset_password_validate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account.objects.get(pk=uid)
    except(TypeError,ValueError,OverflowError,Account.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user,token):
        request.session['id'] = uid
        messages.success(request,'Please reset your password')
        return redirect('resetPassword')
    else:
        messages.error(request,"Link has been expired")
        return redirect('register')
    
def resetPassword(request):
    if request.method == 'POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            uid = request.session['id']
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request,"Password reset successfully")
            return redirect('login')
        else:
            messages.error(request,"Password doesn't match")
            return redirect('resetPassword')
    else:
        return render(request,'accounts/resetPassword.html')
    
    
@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user,is_ordered=True).order_by('-created_at')
    context = {
        'orders':orders,
    }
    return render(request, 'accounts/my_orders.html',context)


@login_required(login_url='login')
def edit_profile(request):
    userprofile = get_object_or_404(UserProfile,user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST,instance=request.user)
        user_profile_form = UserProfileForm(request.POST,request.FILES, instance=userprofile)
        if user_form.is_valid() and user_profile_form.is_valid():
            user_form.save()
            user_profile_form.save()
            messages.success(request,"Your profile has been updated")
            return redirect('edit_profile')
    else:
        user_form = UserForm(instance=request.user)
        user_profile_form = UserProfileForm(instance=userprofile)
    context = {
        'user_form':user_form,
        'user_profile_form':user_profile_form,
        'userprofile':userprofile,
    } 
    return render(request,'accounts/edit_profile.html',context)   


@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']
        confirm_password = request.POST['confirm_password']

        user = Account.objects.get(username__exact=request.user.username)
        if new_password == confirm_password:
            succeed = user.check_password(current_password)
            if succeed:
                user.set_password(new_password)
                user.save()
                messages.success(request,"Password updated successfully")
                return redirect('change_password')
            else:
                messages.error(request,"Current password is not valid")
                return redirect('change_password')
        else:
            messages.error(request,"Password not matched")
            return redirect('change_password')
    return render(request,'accounts/change_password.html')

def order_detail(request,order_id):
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    order = Order.objects.get(order_number = order_id)
    subtotal = 0
    for i in order_detail:
        subtotal += i.product_price * i.quantity
    context = {
        'order_detail':order_detail,
        'order':order,
        'subtotal':subtotal,
    }
    return render(request,"accounts/order_detail.html",context)
