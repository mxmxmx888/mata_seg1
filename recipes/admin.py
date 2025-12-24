from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from recipes.models.user import User
from recipes.models.recipe_post import RecipePost
from recipes.models.comment import Comment
from recipes.models.report import Report 

class ReportInline(admin.StackedInline):
    """Show reports directly on the Recipe/Comment page in Admin."""
    model = Report
    extra = 0
    readonly_fields = ['reporter', 'reason', 'description', 'created_at']
    
    def get_queryset(self, request):
        """Only show unresolved reports inline."""
        return super().get_queryset(request).filter(is_resolved=False)

@admin.register(RecipePost)
class RecipePostAdmin(admin.ModelAdmin):
    """Admin configuration for recipe posts with moderation actions."""
    list_display = ('title', 'author', 'created_at', 'is_hidden', 'report_count_display')
    list_filter = ('is_hidden', 'created_at')
    search_fields = ('title', 'description', 'author__username')
    actions = ['hide_content', 'approve_content']
    inlines = [ReportInline]

    def report_count_display(self, obj):
        """Return formatted count of unresolved reports."""
        count = obj.reports.filter(is_resolved=False).count()
        if count > 0:
            return format_html('<span style="color:red; font-weight:bold;">{} Reports</span>', count)
        return "0"
    report_count_display.short_description = "Active Reports"

    @admin.action(description='Hide selected recipes (Remove)')
    def hide_content(self, request, queryset):
        """Mark selected recipes as hidden."""
        queryset.update(is_hidden=True)

    @admin.action(description='Approve selected recipes (Unhide)')
    def approve_content(self, request, queryset):
        """Unhide selected recipes."""
        queryset.update(is_hidden=False)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Admin configuration for comments with moderation actions."""
    list_display = ('short_text', 'user', 'recipe_post', 'is_hidden', 'report_count_display')
    list_filter = ('is_hidden', 'created_at')
    search_fields = ('text', 'user__username')
    actions = ['hide_content', 'approve_content']

    def short_text(self, obj):
        """Shorten comment text for list display."""
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    def report_count_display(self, obj):
        """Return formatted count of unresolved comment reports."""
        count = obj.reports.filter(is_resolved=False).count()
        if count > 0:
            return format_html('<span style="color:red; font-weight:bold;">{} Reports</span>', count)
        return "0"
    report_count_display.short_description = "Active Reports"

    @admin.action(description='Hide selected comments')
    def hide_content(self, request, queryset):
        """Mark selected comments as hidden."""
        queryset.update(is_hidden=True)

    @admin.action(description='Approve/Unhide comments')
    def approve_content(self, request, queryset):
        """Unhide selected comments."""
        queryset.update(is_hidden=False)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin configuration for user-submitted reports."""
    list_display = ('target_object', 'reason', 'reporter', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'reason', 'created_at')
    actions = ['mark_resolved']

    def target_object(self, obj):
        """Return a link to the reported object for quick navigation."""
        if obj.recipe_post:
            link = reverse("admin:recipes_recipepost_change", args=[obj.recipe_post.id])
            return format_html('<a href="{}">Recipe: {}</a>', link, obj.recipe_post.title)
        elif obj.comment:
            link = reverse("admin:recipes_comment_change", args=[obj.comment.id])
            return format_html('<a href="{}">Comment: {}</a>', link, obj.comment.id)
        return "Deleted Content"
    target_object.short_description = "Reported Content"

    @admin.action(description='Mark selected reports as Resolved')
    def mark_resolved(self, request, queryset):
        """Mark selected reports resolved."""
        queryset.update(is_resolved=True)
