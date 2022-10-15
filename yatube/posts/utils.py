from django.conf import settings
from django.core.paginator import Paginator


def get_page(request, post_list):
    paginator = Paginator(post_list, settings.NUMBER_OBJECTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
