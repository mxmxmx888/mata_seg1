from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from recipes.models import Ingredient
from django.db.models import Q

@login_required
def shop(request):
    items = (
        Ingredient.objects.filter(
            Q(shop_url__isnull=False) & ~Q(shop_url__regex=r'^\s*$')
        )
        .select_related('recipe_post')
        .order_by('-id')
    )
    return render(request, 'shop.html', {'items': items})
