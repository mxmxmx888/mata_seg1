user_fixtures = [
    {"username": "@johndoe", "email": "john.doe@example.org", "first_name": "John", "last_name": "Doe"},
    {"username": "@janedoe", "email": "jane.doe@example.org", "first_name": "Jane", "last_name": "Doe"},
    {"username": "@charlie", "email": "charlie.johnson@example.org", "first_name": "Charlie", "last_name": "Johnson"},
]

recipe_image_file_pool = [
    "static/post_images/meal1.jpg",
    "static/post_images/meal2.jpg",
    "static/post_images/meal3.jpg",
    "static/post_images/meal4.jpg",
    "static/post_images/meal5.jpg",
    "static/post_images/meal6.jpg",
    "static/post_images/meal7.jpg",
    "static/post_images/meal8.jpg",
]

BASE_INGREDIENT_POOL = [
    "salt",
    "black pepper",
    "olive oil",
    "garlic cloves",
    "red onion",
    "cherry tomatoes",
    "parmesan",
    "fresh basil",
    "chicken breast",
    "smoked paprika",
    "ground cumin",
    "yogurt",
    "baby spinach",
    "mushrooms",
    "lemon juice",
    "soy sauce",
    "white rice",
    "pasta",
    "butter",
    "all-purpose flour",
    "granulated sugar",
    "eggs",
    "milk",
]

SHOP_PRODUCTS = [
    {
        "name": "Pickles",
        "shop_url": "https://groceries.morrisons.com/products/Baxters-Whole-Gherkins/115468261",
        "shop_image": "static/shop_images/Pickles.jpg",
    },
    {
        "name": "Honey",
        "shop_url": "https://thelondonhoneycompany.com/products/pure-honey-london-honey-jar-250g",
        "shop_image": "static/shop_images/Honey.jpg",
    },
    {
        "name": "Garlic Spread",
        "shop_url": "https://www.bralasbest.com/product/original",
        "shop_image": "static/shop_images/GarlicSpread.jpg",
    },
    {
        "name": "Cipher Herbs",
        "shop_url": "https://www.herbalista.in/products/lemon-green-tea-20-cotton-teabags",
        "shop_image": "static/shop_images/Herbs.jpg",
    },
    {
        "name": "Bowl",
        "shop_url": "https://cafeauclay.com/collections/handbuilding",
        "shop_image": "static/shop_images/Bowl.jpg",
    },
    {
        "name": "Bowls",
        "shop_url": "https://argotstudio.com/en-gb/products/acorn-bowl-grand",
        "shop_image": "static/shop_images/Bowl2.jpg",
    },
    {
        "name": "Ginger",
        "shop_url": "https://www.tesco.com/groceries/en-GB/products/314931777",
        "shop_image": "static/shop_images/Ginger.jpg",
    },
    {
        "name": "Designer Forks",
        "shop_url": "https://www.pamono.eu/model-7000-danube-cutlery-by-janos-megyik-for-amboss-1970s-set-of-24",
        "shop_image": "static/shop_images/Forks.jpg",
    },
    {
        "name": "Flour",
        "shop_url": "https://www.lakeland.co.uk/43784/mcdougalls-vintage-flour-tin",
        "shop_image": "static/shop_images/Flour.jpg",
    },
    {
        "name": "Saga Performance Powder",
        "shop_url": "https://treasonfoods.com/en-gb",
        "shop_image": "static/shop_images/SagaPerformancePowder.jpg",
    },
    {
        "name": "Form Perfomance Protein",
        "shop_url": "https://formnutrition.com/plant-based-nutrition/form-performance-plant-based-vegan-protein-powder/",
        "shop_image": "static/shop_images/FormPerformanceProtein.jpg",
    },
    {
        "name": "Choc Protein Spread",
        "shop_url": "https://cokokremy.heureka.cz/got7-nutrition-premium-protein-spread-nut-nougat-choco-smooth-250-g/",
        "shop_image": "static/shop_images/ChocSpread.jpg",
    },
    {
        "name": "Habits Gummies",
        "shop_url": "https://asrar-co.com/ar/هابيتس-بيوتين-مكمل-غذائي-للشعر-والبشرة-والأظافر-60-قطعة-حلوى/p612828170",
        "shop_image": "static/shop_images/Gummies.jpg",
    },
    {
        "name": "Nerikomi plate",
        "shop_url": "https://shopquarters.com/products/green-on-green-nerikomi-plate",
        "shop_image": "static/shop_images/Plate.jpg",
    },
]


shop_image_file_pool = sorted({p["shop_image"] for p in SHOP_PRODUCTS})
SHOP_IMAGE_MAP = {p["name"].lower(): p["shop_image"] for p in SHOP_PRODUCTS}
SHOP_ITEM_OVERRIDES = {
    p["name"].lower(): {
        "shop_url": p["shop_url"],
        "shop_image": p["shop_image"],
    }
    for p in SHOP_PRODUCTS
}

def _chunk_products(products, size=5):
    """Split SHOP_PRODUCTS into fixed-size groups for seeding ingredients per recipe."""
    chunk = []
    for idx, prod in enumerate(products, start=1):
        chunk.append({"name": prod["name"], "shop_url": prod["shop_url"]})
        if idx % size == 0:
            yield chunk
            chunk = []
    if chunk:
        yield chunk

# Auto-generated ingredient sets derived from SHOP_PRODUCTS (no duplicate config needed)
SHOP_INGREDIENT_SETS = list(_chunk_products(SHOP_PRODUCTS, size=5))

categories = ["Breakfast", "Lunch", "Dinner", "Dessert", "Vegan"]
tags_pool = ["quick", "family", "spicy", "budget", "comfort", "healthy", "high_protein", "low_carb"]

favourite_names = [
    "favourites",
    "dinner ideas",
    "quick meals",
    "healthy",
    "desserts",
    "meal prep",
    "date night",
    "budget",
]

comment_phrases = [
    "Amazing!!",
    "Looks yummy",
    "Okay that has to be my favourite",
    "Definitely will be trying this out",
    "need this asap",
    "ok wow",
    "this looks so good",
    "made it last night, 10/10",
    "savingggg",
    "what did u use for the sauce?",
    "can i swap chicken for tofu??",
    "how spicy is it tho",
    "love how simple this is",
    "that sauce 😭",
    "comfort food fr",
    "added extra garlic and yeah... wow",
    "my kinda meal",
    "is this air fryer friendly or nah",
    "how long it keep in the fridge?",
    "freezer ok??",
    "any sub for cream",
    "i tried it and it slapped",
    "presentation on point",
    "macros??",
    "pls drop the measurements",
    "do i have to marinate or can i skip",
    "what pasta is that",
    "can i use greek yogurt instead?",
    "this is going on my list",
]

bio_phrases = [
    "home cook who loves quick meals",
    "always experimenting with new flavours",
    "Meal prep enthusiast and pasta fan",
    "baking on weekends, cooking every day",
    "trying to eat healthier without losing taste",
    "BIG on comfort food and family dinners",
    "spice lover, especially in curries and stews",
    "Student cook learning one recipe at a time",
    "foodie who believes butter fixes everything",
    "i cook, i taste, i improvise",
]
