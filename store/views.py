from django.shortcuts import render,get_object_or_404, redirect
from django.http import Http404
from .models import Product, ReviewRating, ProductGallery
from category.models import Category
from cart.models import CartItem
from cart.views import _cart_id
from django.core.paginator import EmptyPage,Paginator,PageNotAnInteger
from django.http import HttpResponse
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from .forms import ReviewForm
from django.contrib import messages
from orders.models import OrderProduct

# Create your views here.
def store(request,category_slug=None):
    products = None
    categories = None
    if category_slug != None:
        categories = get_object_or_404(Category,slug = category_slug)
        products = Product.objects.filter(category = categories,is_avalable = True)
        paginator = Paginator(products,3)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()
    else:    
        products = Product.objects.all().filter(is_avalable = True).order_by('id')
        paginator = Paginator(products,3)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()
    context = {
        'products':paged_products,
        'product_count':product_count,
    }
    return render(request,'store/store.html',context)

def product_detail(request,category_slug,product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug,slug=product_slug)
        in_cart = CartItem.objects.filter(cart__cart_id = _cart_id(request),product = single_product).exists()

    except Product.DoesNotExist:
        raise Http404("Product not found")
    
    if request.user.is_authenticated:
        try:
            order_product = OrderProduct.objects.filter(user=request.user,product_id=single_product.id).exists()
        except OrderProduct.DoesNotExist:
            order_product = None
    else:
        order_product = None
    reviews = ReviewRating.objects.filter(product_id=single_product.id,status=True)
    product_gallery = ProductGallery.objects.filter(product=single_product.id)

    context = {
        'single_product':single_product,
        'in_cart':in_cart,
        'order_product':order_product,
        'reviews':reviews,
        'product_gallery':product_gallery,
    }
    return render(request,'store/product_detail.html',context)

def search(request):
    products = Product.objects.none()  # Default empty queryset
    product_count = 0
    
    if 'keyword' in request.GET:
        keyword = request.GET['keyword'].strip()  # Strip whitespace from the keyword
        if keyword:  # Check if keyword is not empty
            products = Product.objects.filter(
                Q(description__icontains=keyword) | Q(product_name__icontains=keyword)
            ).order_by('created_date')
            product_count = products.count()
        else:
            products = Product.objects.all()  # If keyword is empty, show all products
            product_count = products.count()

    context = {
        'products': products,
        'product_count': product_count,
    }
    
    return render(request, 'store/store.html', context)

def submit_review(request,product_id):
    url = request.META.get('HTTP_REFERER')
    if request.method == 'POST':
        try:
            review = ReviewRating.objects.get(product__id=product_id,user__id=request.user.id)
            form = ReviewForm(request.POST, instance=review)
            form.save()
            messages.success(request,"Thank you! Your review has been updated")
            return redirect(url)

        except ReviewRating.DoesNotExist:
            form = ReviewForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.product_id = product_id
                data.user_id = request.user.id
                data.subject = form.cleaned_data['subject']
                data.review = form.cleaned_data['review']
                data.rating = form.cleaned_data['rating']
                data.ip = request.META.get('REMOTE_ADDR')
                data.save()
                messages.success(request,"Thank you! Your review has been submitted")
                return redirect(url)


