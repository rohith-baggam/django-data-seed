
from django_data_seed.utils.get_user import set_current_user
from django.utils.deprecation import MiddlewareMixin


class CurrentUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        """
        Set the current user based on the request object.
        """
        if hasattr(request, 'user'):
            user = request.user
            if user.is_authenticated:
                set_current_user(user)
            else:
                # ? Optional: Handle cases where user is not authenticated
                set_current_user(None)
        else:
            # ? Optional: Handle cases where request.user is not set
            set_current_user(None)

    def process_response(self, request, response):
        """
        Called after the view has been processed.
        """
        return response


class QueryAuthMiddleware:
    """
    Custom middleware to handle JWT authentication from query strings or headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Exception as e:
            print('__call_ Exception ', e)
        if hasattr(request, 'user'):
            user = request.user
            if user.is_authenticated:
                set_current_user(user)
            else:
                # ? Optional: Handle cases where user is not authenticated
                set_current_user(None)
        else:
            # ? Optional: Handle cases where request.user is not set
            set_current_user(None)
        return response
