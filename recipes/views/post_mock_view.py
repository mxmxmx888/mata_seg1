from django.shortcuts import render
from django.templatetags.static import static


def mock_post_detail(request):
    # later this will pull a real Post from the DB
    context = {
        "title": "15-minute garlic butter pasta",
        "author_name": "Ayan",
        "author_handle": "@ayan",
        "cook_time": "15 min",
        "serves": 2,
        "image_url": static("img/hero-salad.jpg"),
        "gallery_images": [
            static("img/lemon-chicken.jpg"),
            static("img/lasagne.jpg"),
            static("img/brownies.jpg"),
        ],
        "video_url": "https://storage.googleapis.com/coverr-main/mp4/Footage%20Of%20Pasta.mp4",
        "summary": "Quick comfort food for busy nights. Butter, garlic and herbs coat hot pasta for a cozy dinner in minutes.",
        "ingredients": [
            "200g spaghetti",
            "3 cloves garlic, finely sliced",
            "40g butter",
            "Handful of parsley, chopped",
            "Salt & pepper",
        ],
        "steps": [
            "Boil the pasta in salted water until al dente.",
            "Gently fry the garlic in butter until fragrant.",
            "Add cooked pasta with a splash of pasta water and toss.",
            "Finish with parsley, salt and pepper.",
        ],
        "tags": ["weeknight", "butter", "garlic", "comfort food"],
        "pair_with": [
            {
                "title": "Charred broccoli salad",
                "summary": "Bright greens with lemon + tahini",
                "image": static("img/hero-salad.jpg"),
                "url": "#"
            },
            {
                "title": "Crisp garlic bread",
                "summary": "Crunchy side with herbs",
                "image": static("img/lasagne.jpg"),
                "url": "#"
            },
        ],
        "view_similar": [
            {
                "title": "Zesty pesto pasta",
                "description": "Herby weeknight pasta",
                "image": static("img/lemon-chicken.jpg"),
                "url": "#"
            },
            {
                "title": "Tomato confit linguine",
                "description": "Slow confit sauce",
                "image": static("img/brownies.jpg"),
                "url": "#"
            },
            {
                "title": "Cacio e pepe",
                "description": "Creamy Roman staple",
                "image": static("img/hero-salad.jpg"),
                "url": "#"
            },
            {
                "title": "Garlic chili oil noodles",
                "description": "Spicy pantry pasta",
                "image": static("img/lasagne.jpg"),
                "url": "#"
            },
            {
                "title": "Roasted tomato soup",
                "description": "Silky sides",
                "image": static("img/lemon-chicken.jpg"),
                "url": "#"
            },
            {
                "title": "Whipped ricotta toast",
                "description": "Bright brunch snack",
                "image": static("img/brownies.jpg"),
                "url": "#"
            },
            {
                "title": "Lemon herb chicken",
                "description": "Protein pairing",
                "image": static("img/lemon-chicken.jpg"),
                "url": "#"
            },
            {
                "title": "Spring greens risotto",
                "description": "Creamy greens",
                "image": static("img/hero-salad.jpg"),
                "url": "#"
            },
        ],
        "post_date": "JUN. 4, 2023",
        "source_label": "Staircase detail by architect",
        "source_tag": "Woosang Kim",
        "source_link": "#",
        "source_author": "@bymoho",
        "source_platform": "Instagram",
        "connections": [
            {"name": "details", "handle": "@lp001", "elements": 32, "avatar_url": "https://images.unsplash.com/photo-1544723795-3fb6469f5b39", "rank": "1st"},
            {"name": "interiors", "handle": "@imjake", "elements": 197, "avatar_url": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d"},
            {"name": "stair", "handle": "@brooklyn", "elements": 167, "avatar_url": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1", "verified": True},
            {"name": "Inspiration", "handle": "@delahuntagram", "elements": 576, "avatar_color": "radial-gradient(circle at 20% 20%, #fbc2eb, #a18cd1)"},
            {"name": "smabs", "handle": "@ari", "elements": 134, "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330", "verified": True},
            {"name": "cut & inside", "handle": "@roger", "elements": 180, "avatar_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab"},
            {"name": "The Territory", "handle": "@irvingdiptera", "elements": 92, "avatar_url": "https://images.unsplash.com/photo-1504593811423-6dd665756598", "verified": True},
            {"name": "ibelieveinufos", "handle": "@veteene", "elements": 491, "avatar_color": "radial-gradient(circle at 30% 30%, #f6d365, #fda085)"},
            {"name": "Inevitable Project", "handle": "@bonedry", "elements": 431, "avatar_color": "radial-gradient(circle at 30% 30%, #ff9a9e, #fad0c4)"},
            {"name": "Ocean Poet", "handle": "@dd228", "elements": 339, "avatar_url": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?crop=faces&fit=crop&w=200&h=200"},
            {"name": "dor_", "handle": "@tania", "elements": 34, "avatar_url": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1", "verified": True},
            {"name": "monday of curiosities", "handle": "@gaiavenire", "elements": 976, "avatar_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330"},
            {"name": "concrete", "handle": "@sanstire", "elements": 201, "avatar_url": "https://images.unsplash.com/photo-1503023345310-bd7c1de61c7d"},
            {"name": "architorturedsoul", "handle": "@veteene", "elements": 71, "avatar_color": "radial-gradient(circle at 30% 30%, #ebbba7, #cfc7f8)"},
        ],
    }
    return render(request, "post/post_detail.html", context)
