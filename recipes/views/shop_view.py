from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from recipes.models import Ingredient

@login_required
def shop(request):
    """
    Display a gallery of ingredients that have shopping links.
    """
    items = Ingredient.objects.filter(shop_url__isnull=False).exclude(shop_url__exact='').select_related('recipe_post').order_by('-id')
    
    return render(request, 'shop.html', {'items': items})