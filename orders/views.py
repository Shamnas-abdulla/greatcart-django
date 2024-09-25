from django.shortcuts import render, redirect
from cart.models import CartItem
from .forms import OrderForm
from .models import Order, Payment, OrderProduct
import datetime
import json
from django.http import JsonResponse
from store.models import Product
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
# Create your views here.
def payments(request):
    body = json.loads(request.body)
    
    # Get the order
    order = Order.objects.filter(user=request.user, is_ordered=False, order_number=body['orderID']).first()
    if order is None:
        return JsonResponse({'error': 'Order not found'}, status=404)

    # Create the payment object
    payment = Payment.objects.create(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total,  # Now this works because order is a single object
        status=body['status']
    )
    payment.save()

    # Update the order
    order.payment = payment
    order.is_ordered = True
    order.save()

    # Move cart items to the order product table
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        order_product = OrderProduct()
        order_product.order_id = order.id
        order_product.payment = payment
        order_product.user = request.user
        order_product.product = item.product
        order_product.quantity = item.quantity
        order_product.product_price = item.product.price
        order_product.ordered = True
        order_product.save()

        cart_item = CartItem.objects.get(id=item.id)
        product_variation = cart_item.variations.all()
        order_product = OrderProduct.objects.get(id=order_product.id)
        order_product.variations.set(product_variation)
        order_product.save()

        #Reduce the quantity of sold product
        product = Product.objects.get(id=item.product_id)
        product.stock -= item.quantity
        product.save()

    #clear cart
    CartItem.objects.filter(user=request.user).delete()

    #Send order recieved email to customer
    mail_subject = "Thank you for your order!"
    message = render_to_string('orders/order_recieved_email.html', {
        'user': request.user,
        'order':order
    })
    to_email = request.user.email
    send_email = EmailMessage(
        mail_subject,
        message,
        to=[to_email]
    )
    send_email.send()

    #Send order number and transaction id sendData method via JsonResponse
    data = {
        'order_number':order.order_number,
        'transID':payment.payment_id,
    }

    return JsonResponse(data)


def place_order(request, total=0):
    current_user = request.user
    cart_items = CartItem.objects.filter(user = current_user)
    item_count = cart_items.count()
    if item_count <= 0:
        return redirect('store')
    
    grand_total = 0
    tax = 0
    for item in cart_items:
        total += (item.product.price * item.quantity)
    tax = (2 * total)/100
    grand_total = total + tax
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()
            #Generate order_number
            yr = int(datetime.date.today().strftime('%Y'))
            mt = int(datetime.date.today().strftime('%m'))
            dt = int(datetime.date.today().strftime('%d'))
            d = datetime.date(yr,mt,dt)
            current_date = d.strftime('%Y%m%d')
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()
            order = Order.objects.get(user=current_user,is_ordered=False,order_number=order_number)
            context = {
                'order':order,
                'cart_items':cart_items,
                'total':total,
                'tax':tax,
                'grand_total':grand_total,
            }
            return render(request,'orders/payments.html',context)
        else:
            return redirect('checkout')
        

def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')
    try:
        order = Order.objects.get(order_number=order_number,is_ordered=True)
        ordered_product = OrderProduct.objects.filter(order_id=order.id)
        payment = Payment.objects.get(payment_id=transID)

        sub_total = 0
        for i in ordered_product:
            sub_total += i.product_price * i.quantity

        context = {
            'order':order,
            'order_product':ordered_product,
            'order_number':order.order_number,
            'transID':payment.payment_id,
            'payment':payment,
            'sub_total':sub_total,
        }
        return render(request,'orders/order_completed.html',context)
    except (Payment.DoesNotExist, Order.DoesNotExist):
        return redirect('home')


